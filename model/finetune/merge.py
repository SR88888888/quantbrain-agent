"""
AWQ模型 + LoRA 部署说明

AWQ模型不建议直接合并LoRA权重。推荐使用vLLM动态加载:

  vllm serve /datadisk/home/lsr/qwen2.5-72b-awq \
    --enable-lora \
    --lora-modules finance-lora=qwen2.5-72b-awq-lora \
    --max-lora-rank 16

调用时: model="finance-lora" 使用微调版本
"""
import sys
import os


def print_usage():
    print("=" * 60)
    print("Qwen2.5-72B-AWQ + LoRA 推荐部署方式")
    print("=" * 60)
    print()
    print("vllm serve /datadisk/home/lsr/qwen2.5-72b-awq \\")
    print("    --host 0.0.0.0 --port 11434 \\")
    print("    --enable-lora \\")
    print("    --lora-modules finance-lora=qwen2.5-72b-awq-lora \\")
    print("    --max-lora-rank 16")
    print()
    print(".env配置:")
    print("  LLM_BASE_URL=http://localhost:11434")
    print("  MODEL_NAME=/datadisk/home/lsr/qwen2.5-72b-awq")
    print()
    print('使用LoRA: 调用时指定 model="finance-lora"')
    print("=" * 60)


def merge_if_needed():
    """如果确实需要合并(不推荐)"""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        print("需要: pip install torch transformers peft")
        return

    BASE = "/datadisk/home/lsr/qwen2.5-72b-awq"
    LORA = "qwen2.5-72b-awq-lora"
    OUT = "qwen2.5-72b-merged"

    confirm = input("AWQ模型合并LoRA可能损失精度,确定继续? (yes/no): ")
    if confirm != "yes":
        return

    print("加载模型...")
    tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, LORA)
    model = model.merge_and_unload()
    os.makedirs(OUT, exist_ok=True)
    model.save_pretrained(OUT)
    tokenizer.save_pretrained(OUT)
    print(f"合并完成: {OUT}")


if __name__ == "__main__":
    if "--merge" in sys.argv:
        merge_if_needed()
    else:
        print_usage()
