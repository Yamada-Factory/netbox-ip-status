def xml_to_dict(element):
    node = {}

    if element.attrib:
        node.update(element.attrib)

    for child in element:
        child_tag = child.tag
        child_dict = xml_to_dict(child)
        if child_tag in node:
            if not isinstance(node[child_tag], list):
                node[child_tag] = [node[child_tag]]
            node[child_tag].append(child_dict)
        else:
            node[child_tag] = child_dict
    return node

# if __name__ == "__main__":
#     import subprocess
#     import xml.etree.ElementTree as ET
#     import json

#     cmd = ['nmap', '-v', '-sn', '-n', '-oX', '-', '192.168.0.0/24']
#     print("Nmap command: " + ' '.join(cmd))
#     result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
#     element = ET.fromstring(result.stdout)
#     # nmap.xml で 保存
#     with open('nmap.xml', 'w') as f:
#         f.write(result.stdout)

#     xml_dict = xml_to_dict(element)
#     json_string = json.dumps(xml_dict, indent=4)
#     # json で 保存
#     with open('nmap.json', 'w') as f:
#         f.write(json_string)
