resource "tls_private_key" "vm_ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_sensitive_file" "private_key" {
  filename        = "${path.module}/${var.key_name}-key.pem"
  content         = tls_private_key.vm_ssh.private_key_pem
  file_permission = "0400"
}

resource "local_file" "public_key" {
  filename = "${path.module}/${var.key_name}-key.pub"
  content  = tls_private_key.vm_ssh.public_key_openssh
}

resource "nebius_compute_v1_disk" "boot" {
  name             = "${var.instance_name}-boot"
  parent_id        = var.project_id
  size_gibibytes   = var.boot_disk_size_gib
  type             = "NETWORK_SSD"
  block_size_bytes = 4096

  source_image_family = {
    image_family = var.boot_disk_image_family
  }
}

locals {
  cloud_init_user_data = <<-EOT
    #cloud-config
    users:
      - name: ${var.ssh_username}
        sudo: ALL=(ALL) NOPASSWD:ALL
        shell: /bin/bash
        ssh_authorized_keys:
          - ${trimspace(tls_private_key.vm_ssh.public_key_openssh)}
    package_update: true
    packages:
      - git
      - python3-dev
      - python3-venv
    runcmd:
      - mkdir -p /home/${var.ssh_username}/gpu_and_inference_hw
      - chown -R ${var.ssh_username}:${var.ssh_username} /home/${var.ssh_username}
  EOT
}

resource "nebius_compute_v1_instance" "gpu_vm" {
  name      = var.instance_name
  parent_id = var.project_id

  resources = {
    platform = var.gpu_platform
    preset   = var.gpu_preset
  }

  boot_disk = {
    existing_disk = {
      id = nebius_compute_v1_disk.boot.id
    }
    attach_mode = "READ_WRITE"
  }

  cloud_init_user_data = local.cloud_init_user_data

  network_interfaces = [
    {
      name       = "eth0"
      subnet_id  = data.nebius_vpc_v1_subnet.default.id
      ip_address = {}
      # Dynamic public IP so you can SSH from your laptop.
      public_ip_address = {}
    }
  ]
}
