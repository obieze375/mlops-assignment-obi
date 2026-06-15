data "nebius_vpc_v1_subnet" "default" {
  name      = var.subnet_name
  parent_id = var.project_id
}
