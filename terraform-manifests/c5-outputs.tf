locals {
  public_ip = try(
    split("/", nebius_compute_v1_instance.gpu_vm.status.network_interfaces[0].public_ip_address.address)[0],
    null
  )
}

output "instance_id" {
  description = "Nebius compute instance ID"
  value       = nebius_compute_v1_instance.gpu_vm.id
}

output "instance_name" {
  description = "Compute instance name"
  value       = nebius_compute_v1_instance.gpu_vm.name
}

output "public_ip" {
  description = "Public IPv4 address of the GPU VM"
  value       = local.public_ip
}

output "ssh_private_key_path" {
  description = "Path to the generated SSH private key (relative to terraform-manifests/)"
  value       = local_sensitive_file.private_key.filename
}

output "ssh_command" {
  description = "Copy-paste command to SSH into the GPU VM"
  value       = local.public_ip != null ? "ssh -i ${var.key_name}-key.pem ${var.ssh_username}@${local.public_ip}" : "Run terraform apply again once the VM has a public IP"
}

output "homework_setup_commands" {
  description = "Commands to run on the VM after SSH to set up the homework repo"
  value       = <<-EOT
    git clone https://github.com/obieze375/gpu_and_inference_hw-Obi.git ~/gpu_and_inference_hw
    cd ~/gpu_and_inference_hw
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python3 hw1/hw1_task.py
    python3 hw2/hw2_task.py
  EOT
}
