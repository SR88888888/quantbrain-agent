import os
import torch
from transformers import (
    MT5ForConditionalGeneration,
    MT5Tokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq
)
from dataset import DataFactory
from config import Config

def main():
    # 强制离线加载
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    
    model_name = Config.MODEL_NAME
    tokenizer = MT5Tokenizer.from_pretrained(model_name, legacy=False, local_files_only=True)
    model = MT5ForConditionalGeneration.from_pretrained(model_name, local_files_only=True)

    # 启用梯度检查点以节省显存
    model.gradient_checkpointing_enable()

    train_dataset = DataFactory.get_dataset(tokenizer, mode="train")

    training_args = Seq2SeqTrainingArguments(
        output_dir=Config.OUTPUT_DIR,
        per_device_train_batch_size=2,      # 4卡总Batch为8
        gradient_accumulation_steps=8,      # 等效Batch Size为64
        learning_rate=1e-4,
        num_train_epochs=Config.EPOCHS,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,                          # 4090 D 必须开启 bf16
        gradient_checkpointing=True,
        optim="adafactor",                 # 节省显存的优化器
        ddp_find_unused_parameters=False,
        report_to="none",
        dataloader_num_workers=0,           # 设为0以防多进程段错误
        local_rank=int(os.environ.get("LOCAL_RANK", -1))
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model)
    )

    print(f"进程 {os.environ.get('LOCAL_RANK')} 已就绪")
    trainer.train()

    if trainer.is_world_process_zero():
        final_path = os.path.join(Config.OUTPUT_DIR, "final_model")
        model.save_pretrained(final_path)
        tokenizer.save_pretrained(final_path)
        print(f"协作训练完成，模型已保存至: {final_path}")

if __name__ == "__main__":
    main()
