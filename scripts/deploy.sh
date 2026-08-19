#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--model-id MODEL]"
}

deploy_region="us-east-1"
model_id="amazon.nova-lite-v1:0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-id)
      model_id="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

aws cloudformation deploy \
  --template-file cloudformation-tool.yaml \
  --stack-name bug-report-tool-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$deploy_region" \
  --no-fail-on-empty-changeset

function_arn="$(aws cloudformation describe-stacks \
  --region "$deploy_region" \
  --stack-name bug-report-tool-stack \
  --query "Stacks[0].Outputs[?OutputKey=='BugReportFunctionArn'].OutputValue" \
  --output text)"

if [[ -z "$function_arn" || "$function_arn" == "None" ]]; then
  echo "Could not read BugReportFunctionArn from bug-report-tool-stack." >&2
  exit 1
fi

aws cloudformation deploy \
  --template-file cloudformation-solution.yaml \
  --stack-name customer-support-bedrock-stack \
  --parameter-overrides \
    "BugReportFunctionArn=$function_arn" \
    "ModelId=$model_id" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$deploy_region" \
  --no-fail-on-empty-changeset

aws cloudformation describe-stacks \
  --region "$deploy_region" \
  --stack-name customer-support-bedrock-stack \
  --query 'Stacks[0].Outputs' \
  --output table
