# Nebius L40S GPU VM (Terraform)

Provisions a single **NVIDIA L40S** GPU VM in Nebius AI Cloud for running the HW1/HW2 homework scripts. Configuration matches the TokenFactory / Nebius console setup:

- **Region:** `eu-north1`
- **Platform:** `gpu-l40s-d` (NVIDIA L40S PCIe with AMD Epyc Genoa)
- **Preset:** `1gpu-16vcpu-96gb` (1 GPU, 16 vCPUs, 96 GiB RAM)
- **Boot disk:** Ubuntu 24.04 LTS for NVIDIA GPUs (CUDA 13), 1280 GiB SSD
- **Network:** default subnet with a **dynamic public IP** for SSH
- **SSH:** Terraform generates an RSA key pair and installs the public key via cloud-init

## Prerequisites

1. [Nebius CLI](https://docs.nebius.com/cli/quickstart) installed and authenticated:

   ```bash
   curl -sSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash
   nebius profile create
   ```

2. [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.4

3. Your **project ID** (from Compute → project selector, e.g. `default-project-eu-north1`)

## Deploy

```bash
cd terraform-manifests
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and set project_id

terraform init
terraform plan
terraform apply
```

After apply, Terraform prints:

- `public_ip` — VM public address
- `ssh_command` — ready-to-run SSH command, e.g. `ssh -i nebius-l40s-key.pem obi@<ip>`
- `homework_setup_commands` — clone repo and install Python deps on the VM

The private key is written to `nebius-l40s-key.pem` in this directory (gitignored).

## Authentication options

By default the Nebius provider uses your **default CLI profile**. Alternatives:

```bash
# Short-lived user token (12h)
export NEBIUS_IAM_TOKEN="$(nebius iam get-access-token)"
terraform apply
```

Or configure a service account in `c1-versions.tf` — see [Nebius Terraform authentication](https://docs.nebius.com/terraform-provider/authentication).

## Destroy

```bash
terraform destroy
```

This removes the VM and boot disk.
