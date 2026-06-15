variable "region" {
  description = "Nebius region (must match your project region, e.g. eu-north1)"
  type        = string
  default     = "eu-north1"
}

variable "project_id" {
  description = "Nebius project ID (default-project-eu-north1 in the console)"
  type        = string
}

variable "subnet_name" {
  description = "VPC subnet name (default-subnet in the console)"
  type        = string
  default     = "default-subnet"
}

variable "instance_name" {
  description = "Compute instance name"
  type        = string
  default     = "gpu-homework-l40s"
}

variable "gpu_platform" {
  description = "GPU platform ID"
  type        = string
  default     = "gpu-l40s-d" # NVIDIA L40S PCIe with AMD Epyc Genoa (eu-north1)
}

variable "gpu_preset" {
  description = "GPU preset: 1 GPU, 16 vCPUs, 96 GiB RAM"
  type        = string
  default     = "1gpu-16vcpu-96gb"
}

variable "boot_disk_size_gib" {
  description = "Boot disk size in GiB"
  type        = number
  default     = 1280
}

variable "boot_disk_image_family" {
  description = "Ubuntu 24.04 LTS for NVIDIA GPUs (CUDA 13)"
  type        = string
  default     = "ubuntu24.04-cuda13.0"
}

variable "ssh_username" {
  description = "Linux username for SSH (matches Nebius console credentials profile)"
  type        = string
  default     = "obi"
}

variable "key_name" {
  description = "Prefix for the generated SSH key files"
  type        = string
  default     = "nebius-l40s"
}
