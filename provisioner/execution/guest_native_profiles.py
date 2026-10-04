"""Declared native identity fields for the owned guest handoff profiles.

These fields describe an already observed resource. They confer no native
permission, credential role or directed migration qualification.
"""
from types import MappingProxyType

NATIVE_GUEST_PROFILES = MappingProxyType({
    'openstack': MappingProxyType({'member_identity':'server_id','dmi_matches_native_id':True}),
    'vmware': MappingProxyType({'member_identity':'vm_id','dmi_matches_native_id':False}),
    'nutanix': MappingProxyType({'member_identity':'vm_id','dmi_matches_native_id':False}),
})
