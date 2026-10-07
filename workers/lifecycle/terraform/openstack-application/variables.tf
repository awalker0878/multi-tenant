variable "tenant_id" {
  type        = string
  description = "Owning product tenant identity from the immutable plan."
  validation {
    condition     = can(regex("^[a-f0-9-]{36}$", var.tenant_id))
    error_message = "A concrete product tenant UUID is required."
  }
}

variable "resource_id" {
  type        = string
  description = "Stable application identity; no circular saved-plan digest in metadata."
  validation {
    condition     = can(regex("^[a-f0-9-]{36}$", var.resource_id))
    error_message = "A concrete application UUID is required."
  }
}

variable "project_id" {
  type        = string
  description = "API-discovered, administrator-confirmed OpenStack project identity."
  validation {
    condition     = can(regex("^([a-f0-9]{32}|[a-f0-9-]{36})$", var.project_id))
    error_message = "A concrete OpenStack project identity is required."
  }
}

variable "workloads" {
  description = "Exact discovered IDs and owner-confirmed allocation, image and placement inputs."
  type = map(object({
    name                      = string
    image_id                  = string
    flavor_id                 = string
    volume_type               = string
    root_size_gb              = number
    compute_availability_zone = string
    volume_availability_zone  = string
    key_pair                  = string
    nics = map(object({
      network_id         = string
      subnet_id          = string
      ip_address         = string
      security_group_ids = set(string)
    }))
  }))
  validation {
    condition = (
      length(var.workloads) >= 1 && length(var.workloads) <= 32 &&
      alltrue([for key, w in var.workloads : (
        can(regex("^[a-z][a-z0-9_-]{0,31}$", key)) &&
        w.root_size_gb >= 1 && w.root_size_gb == floor(w.root_size_gb) &&
        length(w.nics) >= 1 && length(w.nics) <= 8 &&
        alltrue([for nic_key, nic in w.nics : (
          can(regex("^[a-z][a-z0-9_-]{0,31}$", nic_key)) &&
          length(nic.security_group_ids) > 0 &&
          can(cidrhost("${nic.ip_address}/${strcontains(nic.ip_address, ":") ? 128 : 32}", 0))
        )])
      )])
    )
    error_message = "Supply bounded workloads, positive integer disk sizes, fixed IPs and explicit security groups."
  }
}
