#!/usr/bin/env bash
# Session staging (docs/roadmap.md, M3.0.10): up / down / status.
#   make staging-up | staging-down | staging-status
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="/usr/bin:/opt/homebrew/bin:$PATH"            # Intel binaries in /usr/local/bin are broken
export AWS_PROFILE="${AWS_PROFILE:-agentforge-tf}"       # credential_process: refreshes during long applies
REGION=us-west-1
CLUSTER=agentforge-staging-core
TF="terraform -chdir=infra/terraform"
VARS="-var-file=envs/staging/staging.tfvars"
PLAN=infra/terraform/staging.tfplan

fail() { echo "ERROR: $*" >&2; exit 1; }

check_login() {
  aws sts get-caller-identity --query Arn --output text >/dev/null 2>&1 \
    || fail "AWS login expired. Run: aws login --profile agentforge"
}

init() {
  [ -f infra/terraform/envs/staging/backend.hcl ] || fail "missing envs/staging/backend.hcl (see backend.hcl.example)"
  $TF init -input=false -backend-config=envs/staging/backend.hcl >/dev/null
}

kubeconfig() {
  aws eks update-kubeconfig --name "$CLUSTER" --region "$REGION" >/dev/null
}

up() {
  check_login
  if [ -z "${TF_VAR_anthropic_api_key:-}" ]; then
    read -rsp "Anthropic API key (hidden): " TF_VAR_anthropic_api_key; echo
    export TF_VAR_anthropic_api_key
  fi
  init
  trap 'rm -f "$PLAN"' EXIT                               # the plan file holds secrets
  $TF plan $VARS -out=staging.tfplan
  read -rp "Apply this plan? (yes/no) " ok
  [ "$ok" = "yes" ] || fail "not applied"
  $TF apply staging.tfplan
  kubeconfig
  kubectl get nodes
}

down() {
  check_login
  init
  # The ALB is created by the controller, not Terraform: remove it first or the VPC can't be deleted.
  if aws eks describe-cluster --name "$CLUSTER" --region "$REGION" >/dev/null 2>&1; then
    kubeconfig
    if helm status agentforge -n agentforge >/dev/null 2>&1; then
      echo "Uninstalling the app (and its load balancer)..."
      helm uninstall agentforge -n agentforge --wait
    fi
  fi
  $TF destroy $VARS                                       # you still type "yes"
  status
}

deploy() {
  check_login
  [ -z "$(git status --porcelain)" ] || fail "uncommitted changes: commit first so the image tag matches the code"
  kubeconfig
  local tag reg ip
  tag=$(git rev-parse --short HEAD)
  reg="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com"
  ip=$(curl -fsS https://checkip.amazonaws.com)
  aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$reg"

  # ECR tags are immutable: build only what isn't pushed yet, so a re-run is safe.
  for c in api-gateway worker migrate studio; do
    if aws ecr describe-images --region "$REGION" --repository-name "agentforge/$c" --image-ids imageTag="$tag" >/dev/null 2>&1; then
      echo "$c:$tag already in ECR, skip"; continue
    fi
    if [ "$c" = studio ]; then
      docker buildx build --platform linux/amd64 --push -t "$reg/agentforge/studio:$tag" \
        --build-arg NEXT_PUBLIC_API_URL=http://agentforge-api-gateway apps/studio
    else
      docker buildx build --platform linux/amd64 --push -t "$reg/agentforge/$c:$tag" --target "$c" .
    fi
  done

  helm upgrade --install agentforge infra/helm/agentforge -n agentforge --create-namespace \
    -f infra/helm/agentforge/values-staging.yaml \
    --set global.imageRegistry="$reg" --set image.tag="$tag" \
    --set-string "apiGateway.ingress.annotations.alb\.ingress\.kubernetes\.io/inbound-cidrs=$ip/32" \
    --set-string "studio.ingress.annotations.alb\.ingress\.kubernetes\.io/inbound-cidrs=$ip/32" \
    --wait --timeout 10m
  kubectl get pods -n agentforge
  echo "URL: http://$(kubectl get ingress -n agentforge -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')"
}

show() { printf '%-16s %s\n' "$1" "${2:-(none)}"; }

status() {
  check_login
  show "EKS clusters:"  "$(aws eks list-clusters --region "$REGION" --query clusters --output text)"
  show "RDS instances:" "$(aws rds describe-db-instances --region "$REGION" --query 'DBInstances[].DBInstanceIdentifier' --output text)"
  show "NAT gateways:"  "$(aws ec2 describe-nat-gateways --region "$REGION" --filter Name=state,Values=available,pending --query 'NatGateways[].NatGatewayId' --output text)"
  show "EC2 running:"   "$(aws ec2 describe-instances --region "$REGION" --filters Name=instance-state-name,Values=running,pending --query 'Reservations[].Instances[].InstanceId' --output text)"
  show "Public IPs:"    "$(aws ec2 describe-addresses --region "$REGION" --query 'Addresses[].PublicIp' --output text)"
  show "Load balancers:" "$(aws elbv2 describe-load-balancers --region "$REGION" --query 'LoadBalancers[].LoadBalancerName' --output text)"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  deploy) deploy ;;
  status) status ;;
  *) fail "usage: $0 up|down|deploy|status" ;;
esac
