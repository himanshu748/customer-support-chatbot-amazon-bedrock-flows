#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--model-id MODEL] [--solution-stack-name NAME]"
}

deploy_region="us-east-1"
model_id="amazon.nova-lite-v1:0"
solution_stack_name="customer-support-flow-stack"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-id)
      model_id="$2"
      shift 2
      ;;
    --solution-stack-name)
      solution_stack_name="$2"
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

aws cloudformation deploy \
  --template-file cloudformation-solution.yaml \
  --stack-name "$solution_stack_name" \
  --parameter-overrides \
    "ModelId=$model_id" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$deploy_region" \
  --no-fail-on-empty-changeset

aws cloudformation describe-stacks \
  --region "$deploy_region" \
  --stack-name "$solution_stack_name" \
  --query 'Stacks[0].Outputs' \
  --output table
