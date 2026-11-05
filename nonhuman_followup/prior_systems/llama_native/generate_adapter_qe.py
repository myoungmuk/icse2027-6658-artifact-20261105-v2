import sys
import time
import warnings
from pathlib import Path
from typing import Optional

import lightning as L
import torch
import json, re

from generate import generate
from lit_llama import Tokenizer
from lit_llama.adapter import LLaMA
from lit_llama.utils import EmptyInitOnDevice, lazy_load, llama_model_lookup
from scripts.prepare_alpaca import generate_prompt
from utils.smooth_bleu import bleu_fromstr
from sklearn.metrics import classification_report
from tqdm import tqdm


def main(
    prompt: str = "",
    input: str = "",
    adapter_path: Optional[Path] = None,
    pretrained_path: Optional[Path] = None,
    tokenizer_path: Optional[Path] = None,
    quantize: Optional[str] = None,
    block_size: int = 2048,
    max_new_tokens: int = 4,
    top_k: int = 1,
    temperature: float = 1,
    test_data_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> None:
    """Generates a response based on a given instruction and an optional input.
    This script will only work with checkpoints from the instruction-tuned LLaMA-Adapter model.
    See `finetune_adapter.py`.

    Args:
        prompt: The prompt/instruction (Alpaca style).
        adapter_path: Path to the checkpoint with trained adapter weights, which are the output of
            `finetune_adapter.py`.
        input: Optional input (Alpaca style).
        pretrained_path: The path to the checkpoint with pretrained LLaMA weights.
        tokenizer_path: The tokenizer path to load.
        quantize: Whether to quantize the model and using which method:
            ``"llm.int8"``: LLM.int8() mode,
            ``"gptq.int4"``: GPTQ 4-bit mode.
        max_new_tokens: The number of generation steps to take.
        top_k: The number of top most probable tokens to consider in the sampling process.
        temperature: A value controlling the randomness of the sampling process. Higher values result in more random
            samples.
    """
    if not adapter_path:
        adapter_path = Path("out/adapter/alpaca/lit-llama-adapter-finetuned.pth")
    if not pretrained_path:
        pretrained_path = Path(f"./checkpoints/lit-llama/7B/lit-llama.pth")
    if not tokenizer_path:
        tokenizer_path = Path("./checkpoints/lit-llama/tokenizer.model")
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        prediction_file_path = output_path / "predictions.txt"
        gold_file_path = output_path / "golds.txt"
    else:
        prediction_file_path = Path("predictions.txt")
        gold_file_path = Path("golds.txt")
    
    assert adapter_path.is_file()
    assert pretrained_path.is_file()
    assert tokenizer_path.is_file()

    fabric = L.Fabric(devices=1)
    dtype = torch.bfloat16 if fabric.device.type == "cuda" and torch.cuda.is_bf16_supported() else torch.float32

    print("Loading model ...", file=sys.stderr)
    t0 = time.time()
    pretrained_checkpoint = lazy_load(pretrained_path)
    adapter_checkpoint = lazy_load(adapter_path)
    name = llama_model_lookup(pretrained_checkpoint)

    with EmptyInitOnDevice(
        device=fabric.device, dtype=dtype, quantization_mode=quantize
    ):
        model = LLaMA.from_name(name)

    # 1. Load the pretrained weights
    model.load_state_dict(pretrained_checkpoint, strict=False)
    # 2. Load the fine-tuned adapter weights
    model.load_state_dict(adapter_checkpoint, strict=False)

    print(f"Time to load model: {time.time() - t0:.02f} seconds.", file=sys.stderr)

    model.eval()
    model = fabric.setup_module(model)

    tokenizer = Tokenizer(tokenizer_path)

    if test_data_path:
        with open(test_data_path, "r") as f:
            test_data = json.load(f)
        fabric.print(f"Loaded {len(test_data)} test samples.")

    golds = []
    preds = []
    t0 = time.time()
    for i, sample in enumerate(tqdm(test_data)):
        input_data = {"instruction": sample["instruction"], "input": sample["input"]}
        prompt = generate_prompt(input_data)
        encoded = tokenizer.my_encode_for_generate(prompt, bos=True, eos=False, device=model.device, max_length=block_size-max_new_tokens)

        output = generate(
            model,
            idx=encoded,
            max_seq_length=block_size,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            eos_id=tokenizer.eos_id
        )

        output = tokenizer.decode(output)
        output = output.split("### Response:\n")[1].strip()
        golds.append(sample["output"])
        preds.append(output)
        if i == 0:
            fabric.print("Instuction: " + sample["instruction"])
            fabric.print("Input: " + sample["input"])
            fabric.print("Output: " + sample["output"])
            fabric.print("Respond: " + output)

    t = time.time() - t0
    with open(gold_file_path, "w") as f:
        for gold in golds:
            f.write(repr(gold)[1:-1] + "\n")
    with open(prediction_file_path, "w") as f:
        for prediction in preds:
            f.write(repr(prediction)[1:-1] + "\n")

    pred_labels = []
    gold_labels = []
    for pred, gold in zip(preds, golds):
        pred = pred.lower()
        gold = gold.lower()
        if "yes" in pred or "true" in pred:
            pred_labels.append(1)
        elif "no" in pred or "false" in pred:
            pred_labels.append(0)
        else:
            fabric.print("there is a prediction that is not yes or no with value: " + pred)
            pred_labels.append(0)
        if "yes" in gold or "true" in gold:
            gold_labels.append(1)
        elif "no" in gold or "false" in gold:
            gold_labels.append(0)
        else:
            fabric.print("there is a gold label that is not yes or no with value: " + gold)
            gold_labels.append(0)
    fabric.print("\n" + classification_report(gold_labels, pred_labels, target_names=["no", "yes"], digits=4))


    fabric.print(f"\n\nTime for inference: {t:.02f} sec total, {len(test_data) / t:.02f} entries/sec")
    if fabric.device.type == "cuda":
        fabric.print(f"Memory used: {torch.cuda.max_memory_reserved() / 1e9:.02f} GB")


if __name__ == "__main__":
    from jsonargparse import CLI

    torch.set_float32_matmul_precision("high")
    warnings.filterwarnings(
        # Triggered internally at ../aten/src/ATen/EmptyTensor.cpp:31
        "ignore", 
        message="ComplexHalf support is experimental and many operators don't support it yet"
    )
    CLI(main)
