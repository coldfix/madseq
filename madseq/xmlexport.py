from xml.etree import ElementTree
from math import pi

rad2deg = 180 / pi


def main(filename):
    tree = ElementTree.parse(filename)
    root = tree.getroot()
    lattice = tree.find('lattice')

    elements = [
        parse_xml_element(xml_elem)
        for xml_elem in lattice
    ]

    pos = 0
    for elem in elements:
        elem['at'] = pos
        pos += elem.get('length', 0)

    from pprint import pprint

    #pprint([el for el in elements
    #        if el['type'] == 'drift' and
    #        not el['name'].startswith('DRIFT')])

    joined = [elements[0]]
    for elem in elements[1:]:
        top = joined[-1]
        if (elem['type'] == 'v_monitor' and
                elem['type'] == 'h_monitor' and
                elem['name'].startswith('VMONITOR') and
                elem['at'] == top['at']):
            top['type'] = 'monitor'
            continue
        if (elem['type'] == 'v_slit' and
                elem['type'] == 'h_slit' and
                elem['name'].startswith('SLIT_V') and
                elem['at'] == top['at']):
            top['type'] = 'slit'
            top['position_top'] = elem['position_left']
            top['position_bottom'] = elem['position_right']
            continue

        joined.append(elem)


    elements = [elem for elem in elements if elem['type'] != 'drift']

    #pprint([b for a, b in zip(elements, elements[1:])
    #        if b['at'] < a['at'] + a.get('length', 0)])

    #pprint(elements)
    #pprint({el['type'] for el in elements})

    for elem in elements:
        try:
            text = format_madx_element(elem)
        except KeyError as e:
            print("ERROR", e, elem)
        if text:
            print("  {:14}{}".format(elem['name']+':', text))


attr_types = {
    'name': str,
    'length': float,
    'height': float,
    'width': float,
    'order': int,
    'kxl': float,
    'position_left': float,
    'slope_rad': float,
    'angle_rad': float,
    'edge_rad_in': float,
    'edge_rad_out': float,
}

def parse_xml_element(xml_elem):
    d = {key: attr_types.get(key, str)(val)
         for key, val in xml_elem.attrib.items()}
    d['type'] = xml_elem.tag
    return d


def format_madx_element(elem_dict):
    type = elem_dict['type']
    attrs = elem_dict.copy()

    if type == 'dipole':
        attrs.update({
            'angle': round(attrs['angle_rad'] * rad2deg, 2),
            'e1': round(attrs['edge_rad_in']  * rad2deg, 2),
            'e2': round(attrs['edge_rad_out'] * rad2deg, 2),
            'dax': 'dax_' + attrs['name'],
            'hgap': 0.0385,
            'fint': 0.35,
        })
        return '''SBEND, L={length}, ANGLE={angle}*deg, E1={e1}*deg, E2={e2}*deg,
                    K0:=({name}->angle + {dax})/{name}->L,
                    HGAP={hgap}, FINT={fint}, at={at:.4f};'''.format(**attrs)

    if type == 'monitor':

    if type == 'h_monitor':
        pass

    if type == 'v_monitor':
        pass

    'slit'
    'dipole'
    'h_monitor'
    'h_slit'
    'multipole'
    'quadrupole'
    'skew_dipole'
    'skew_multipole'
    'solenoid'
    'v_monitor'
    'v_slit'

    return ''


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
