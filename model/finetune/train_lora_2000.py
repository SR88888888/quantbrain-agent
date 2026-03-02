import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import transformers

# === 核心修复补丁：拦截 AutoAWQ 的报错 ===
if not hasattr(transformers.activations, 'PytorchGELUTanh'):
    class PytorchGELUTanh(nn.Module):
        def forward(self, input):
            return F.gelu(input, approximate="tanh")
    transformers.activations.PytorchGELUTanh = PytorchGELUTanh
# ==========================================

from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset

MODEL_PATH = "/datadisk/home/lsr/qwen2.5-72b-awq"
DATASET_PATH = "finetune_data_2000.json"
OUTPUT_DIR = "qwen2.5-72b-awq-lora-v2"

def main():
    print("🚀 开始加载 Tokenizer 与 模型 (准备进行 V2 版本的海量数据微调)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH, device_map="auto", torch_dtype=torch.float16, trust_remote_code=True
    )
    model.config.use_cache = False
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()

    print("🔧 挂载 LoRA 适配器...")
    lora_config = LoraConfig(
        r=16, lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, task_type=TaskType.CAUSAL_LM
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("📚 加载 2000 条蒸馏数据集...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    
    def format_fn(x):
        try:
            return {"text": tokenizer.apply_chat_template(x["messages"], tokenize=False, add_generation_prompt=False)}
        except:
            return {"text": "".join([f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in x["messages"]])}

    dataset = dataset.map(format_fn)
    
    # 修复点1：去掉 padding="max_length"，采用动态长度，防止显存浪费
    def tokenize_fn(examples):
        return tokenizer(examples["text"], truncation=True, max_length=1024)
        
    tokenized = dataset.map(tokenize_fn, remove_columns=dataset.column_names, batched=True)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=2,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8, 
        learning_rate=5e-5,
        warmup_ratio=0.05,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        optim="adamw_torch",
        report_to="none"
    )

    # 修复点2：使用 Causal LM 专用的 DataCollator，自动计算 Loss 和 -100 掩码
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model, 
        args=training_args, 
        train_dataset=tokenized,
        data_collator=data_collator
    )

    print("🔥 开始强力微调...")
    trainer.train()
    
    print(f"💾 保存最终权重至 {OUTPUT_DIR}...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("✅ V2 版本微调彻底完成！")

if __name__ == "__main__":
    main()
