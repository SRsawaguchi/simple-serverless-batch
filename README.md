# simple-serverless-batch

こちらはブログに書いている、AWSでサーバーレスなバッチ処理を作るハンズオンです。  

複数の章がありますが、章ごとにコミットを分けています。  
差分の確認やコードのコピーをしたい場合は、コミット一覧から見たい章のコミットに飛んでください。  

## トップページ
https://www.ohitori.fun/entry/develop-simple-batch-processing-with-full-managed-service-in-aws


## 1章 SAMでプロジェクトを初期化
https://www.ohitori.fun/entry/develop-simple-batch-processing-with-full-managed-service-in-aws_1_init_project


## 2章 DynamoDB LocalとMinioでローカルにインフラを再現
https://www.ohitori.fun/entry/develop-simple-batch-processing-with-full-managed-service-in-aws_2_setup_local_servers


## 3章 ビジネスロジックをLambdaに実装
https://www.ohitori.fun/entry/develop-simple-batch-processing-with-full-managed-service-in-aws-3-lambda


## 4章 EventBridgeでStateMachineをトリガー、デプロイ
https://www.ohitori.fun/entry/develop-simple-batch-processing-with-full-managed-service-in-aws_4_eventbridge_stepfunctions_deploy


## 5章 リファクタリングしてテストを実装
https://www.ohitori.fun/entry/develop-simple-batch-processing-with-full-managed-service-in-aws_5_refactor_and_testing

## 実行コマンド早見表

### デプロイ

```
sam deploy --config-file ./samconfig.toml
```

### リソースを削除
```
aws cloudformation delete-stack \
  --stack-name simple-serverless-batch
```

### ユニットテストの実行
※5章の内容を実装したら実行可能。(`refactoring`ブランチに切り替えた場合に実行可能。) . 

```
python3 -m pytest tests/unit/layer -v
```

### Integrationテストの実行
※5章の内容を実装したら実行可能。(`refactoring`ブランチに切り替えた場合に実行可能。) . 

```
AWS_SAM_STACK_NAME="simple-serverless-batch" python -m pytest tests/integration -v
```
