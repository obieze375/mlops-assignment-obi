variable "project_id" {
  description = "Nebius project ID (parent for all resources)."
  type        = string
}

variable "subnet_id" {
  description = "VPC subnet ID for the VM network interface."
  type        = string
}

variable "vm_name" {
  description = "Name for the H100 assignment VM."
  type        = string
  default     = "mlops-assignment-h100"
}

variable "boot_disk_size_gib" {
  description = "Boot disk size in GiB (model weights + data need headroom)."
  type        = number
  default     = 200
}

variable "ssh_public_key" {
  description = "SSH public key injected via cloud-init for ubuntu user."
  type        = string
  default     = ""
}

variable "repo_url" {
  description = "Git repo URL to clone on first boot (optional)."
  type        = string
  default     = ""
}
