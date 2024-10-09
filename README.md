# no-more-sql

### Usage

1. poetry install
2. Run `accelerate config` - make sure you select 
    - single node training
    - multi-gpu
    - fp16/bf16

3. Launch the train script
`accelerate launch train.py`

4. Run inference script
`python inference.py`


**Convert csv to jsonl format**

```bash
# update the fire command to the function you need
$ python utils.py 'data/train_validation.csv' 'data/train.jsonl'
2024-06-03 19:05:31.791 | INFO     | __main__:csv_to_jsonl:12 - Converted data/train_validation.csv to data/train.jsonl
```

#### Caveats
1. Use python < 3.12 (tested on 3.10)
2. To use multiple GPUs, set `ddp_find_unused_parameters=False` in Training Arguments.
4. Device map is created using `PartialState` from `accelerate`
5. Used `prepare_model_for_kbit_training` from `peft`
