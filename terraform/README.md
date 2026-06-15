# Nebius H100 Terraform

Provisions a single **NVIDIA H100 80GB** VM (`gpu-h100-sxm` / `1gpu-16vcpu-200gb`) for the MLOps assignment.

## Prerequisites

1. [Nebius CLI](https://docs.nebius.com/cli/quickstart) installed and configured.
2. [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5.
3. A Nebius **project ID** and **subnet ID** in `eu-north1` (H100 region).

## Authenticate (service account)

```bash
export SA_ID=$(nebius iam service-account create --name terraform-sa --format json | jq -r '.metadata.id')
export TENANT_ID=$(nebius iam tenant list --format json | jq -r '.items[0].metadata.id')
export EDITORS_GROUP_ID=$(nebius iam group get-by-name --name editors --parent-id "$TENANT_ID" --format json | jq -r '.metadata.id')
nebius iam group-membership create --parent-id "$EDITORS_GROUP_ID" --member-id "$SA_ID"
mkdir -p ~/.nebius/authkey
export AUTHKEY_PRIVATE_PATH=~/.nebius/authkey/private.pem
export AUTHKEY_PUBLIC_PATH=~/.nebius/authkey/public.pem
openssl genrsa -out "$AUTHKEY_PRIVATE_PATH" 4096
openssl rsa -in "$AUTHKEY_PRIVATE_PATH" -outform PEM -pubout -out "$AUTHKEY_PUBLIC_PATH"
export AUTHKEY_PUBLIC_ID=$(nebius iam auth-public-key create --account-service-account-id "$SA_ID" --data "$(cat "$AUTHKEY_PUBLIC_PATH")" --format json | jq -r '.metadata.id')
```

## Deploy

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with project_id, subnet_id, ssh_public_key

terraform init
terraform validate
terraform apply
```

After apply, SSH to the VM:

```bash
terraform output ssh_hint
```

Forward ports for the assignment UIs:

```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -L 3001:localhost:3001 \
    -L 8000:localhost:8000 -L 8001:localhost:8001 ubuntu@<public-ip>
```

## Destroy

```bash
terraform destroy
```
