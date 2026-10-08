"""Deterministic OVF for retained VMDKs and reviewed VMware destination hardware."""

from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

OVF = "http://schemas.dmtf.org/ovf/envelope/1"
RASD = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"
VSSD = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"
VMW = "http://www.vmware.com/schema/ovf"


def descriptor(plan: dict[str, Any], receipts: dict[str, Any]) -> str:
    root = Element(
        "Envelope",
        {"xmlns": OVF, "xmlns:ovf": OVF, "xmlns:rasd": RASD, "xmlns:vssd": VSSD, "xmlns:vmw": VMW},
    )
    references = SubElement(root, "References")
    disks = SubElement(root, "DiskSection")
    SubElement(disks, "Info").text = "Retained migration disks"
    networks = SubElement(root, "NetworkSection")
    SubElement(networks, "Info").text = "Isolated destination networks"
    for disk in plan["disks"]:
        key = disk["key"]
        SubElement(
            references,
            "File",
            {"ovf:id": key, "ovf:href": key + ".vmdk", "ovf:size": str(receipts[key]["size"])},
        )
        SubElement(
            disks,
            "Disk",
            {
                "ovf:diskId": key,
                "ovf:fileRef": key,
                "ovf:capacity": str(disk["virtual_bytes"]),
                "ovf:capacityAllocationUnits": "byte",
                "ovf:format": "http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized",
            },
        )
    for index, _ in enumerate(plan["nics"]):
        SubElement(networks, "Network", {"ovf:name": "quarantine-" + str(index)})
    system = SubElement(root, "VirtualSystem", {"ovf:id": plan["name"]})
    SubElement(system, "Info").text = "Migration copy"
    SubElement(system, "Name").text = plan["name"]
    os = SubElement(
        system, "OperatingSystemSection", {"ovf:id": "1", "vmw:osType": plan["guest_id"]}
    )
    SubElement(os, "Info").text = "Reviewed guest identity"
    hardware = SubElement(system, "VirtualHardwareSection")
    SubElement(hardware, "Info").text = "Reviewed destination hardware"
    spec = SubElement(hardware, "System")
    SubElement(spec, "vssd:InstanceID").text = "0"
    SubElement(spec, "vssd:VirtualSystemIdentifier").text = plan["name"]
    SubElement(spec, "vssd:VirtualSystemType").text = plan["hardware_version"]

    def item(values: dict[str, str]) -> None:
        row = SubElement(hardware, "Item")
        for key, value in values.items():
            SubElement(row, "rasd:" + key).text = value

    item({"InstanceID": "1", "ResourceType": "3", "VirtualQuantity": str(plan["cpu"])})
    item(
        {
            "InstanceID": "2",
            "ResourceType": "4",
            "AllocationUnits": "byte * 2^20",
            "VirtualQuantity": str(plan["memory_mb"]),
        }
    )
    for controller in range((len(plan["disks"]) + 14) // 15):
        item(
            {
                "InstanceID": str(10 + controller),
                "ResourceType": "6",
                "ResourceSubType": "lsilogic",
                "Address": str(controller),
            }
        )
    for index, disk in enumerate(plan["disks"]):
        slot = index % 15
        item(
            {
                "InstanceID": str(100 + index),
                "ResourceType": "17",
                "HostResource": "ovf:/disk/" + disk["key"],
                "Parent": str(10 + index // 15),
                "AddressOnParent": str(slot if slot < 7 else slot + 1),
            }
        )
    for index, _ in enumerate(plan["nics"]):
        item(
            {
                "InstanceID": str(200 + index),
                "ResourceType": "10",
                "ResourceSubType": "VmxNet3",
                "Connection": "quarantine-" + str(index),
                "AutomaticAllocation": "false",
            }
        )
    SubElement(
        hardware,
        "vmw:Config",
        {"ovf:required": "false", "vmw:key": "firmware", "vmw:value": plan["firmware"]},
    )
    return tostring(root, encoding="unicode")
