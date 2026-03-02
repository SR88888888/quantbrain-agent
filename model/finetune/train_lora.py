import torch
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForSeq2Seq
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset

MODEL_PATH = "/datadisk/home/lsr/qwen2.5-72b-awq"
DATASET_PATH = "finetune_data_v2.json"
OUTPUT_DIR = "qwen2.5-72b-awq-lora"

def main():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH, device_map="auto", torch_dtype=torch.float16, trust_remote_code=True
    )
    model.enable_input_require_grads()

    lora_config = LoraConfig(
        r=16, lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, task_type=TaskType.CAUSAL_LM
    )
    model = get_peft_model(model, lora_config)

    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    dataset = dataset.map(lambda x: {"text": tokenizer.apply_chat_template(x["messages"], tokenize=False)})
    tokenized = dataset.map(lambda x: tokenizer(x["text"], truncation=True, max_length=1024), batched=True)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,           # 500条数据建议跑3轮
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8, # 实际 batch_size=8
        learning_rate=1e-4,            # 稳健的学习率
        warmup_ratio=0.1,
        fp16=True,
        logging_steps=10,
        save_strategy="no",            # 500条很快，最后存一次即可
        optim="adamw_torch"
    )

    trainer = Trainer(
        model=model, args=training_args, train_dataset=tokenized,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True)
    )

    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    print("训练完成！")

if __name__ == "__main__":
    main()
