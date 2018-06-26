#!/usr/bin/env python3

import sys
import json


component_info = {
        'vc.ril.camera': {
            'inputs': 0,
            'outputs': 3,
            'same_format_on_in_and_out': False,
        },
        'vc.ril.video_render': {
            'inputs': 1,
            'outputs': 0,
        },
        'vc.ril.isp': {
            'inputs': 1,
            'outputs': 1,
        },
        'vc.ril.video_splitter': {
            'inputs': 1,
            'outputs': 4,
        },
        'vc.ril.source': {
            'inputs': 0,
            'outputs': 1,
        },
}


def mmal_encoding_short_to_full(short):
    return 'MMAL_ENCODING_' + {
            'rgb24': 'RGB24',
            'rgba': 'RGBA',
            'i420': 'I420',
            'opaque': 'OPAQUE',
    }[short.lower()]

def mmal_video_source_pattern_short_to_full(short):
    return 'MMAL_VIDEO_SOURCE_PATTERN_' + {
            'white': 'WHITE',
            'black': 'BLACK',
            'diagonal': 'DIAGONAL',
            'noise': 'NOISE',
            'random': 'RANDOM',
            'colour': 'COLOUR',
            'blocks': 'BLOCKS',
            'swirly': 'SWIRLY',
    }[short.lower()]

class ComponentBaseClass:

    def __init__(self, name, component):
        self.name = name
        self.component = component
        max_inputs = component_info[self.component]['inputs']
        max_outputs = component_info[self.component]['outputs']
        self.input = [{} for i in range(max_inputs)]
        self.output = [{} for i in range(max_outputs)]

    def setup_control_port(self, d):
        if d != {}:
            raise AttributeError('Unknown keys: ' + str([*d.keys()]))

    # Connections and hooks
    def setup_ordinal_port(self, port, d0):
        for k0 in list(d0.keys()):
            if   k0 == 'connect_to':
                l = d0.pop(k0)
                port['connect_to'] = {
                        'name': l[0],
                        'idx': int(l[1]),
                }
            elif k0 == 'hooks':
                port['hooks'] = {}
                d1 = d0.pop(k0)
                for k1 in list(d1.keys()):
                    if   k1 == 'post_setup':
                        port['hooks']['post_setup'] = d1.pop(k1)
                    elif k1 == 'buffer':
                        port['hooks']['buffer'] = d1.pop(k1)
                    else:
                        raise KeyError('Unknown key: hooks.' + k1)

    def presetup_input_port(self, n, d):
        max_inputs = component_info[self.component]['inputs']
        if n >= max_inputs:
            raise KeyError('Component ' + self.component + ' do not have ' +
                    'input port ' + str(n))

    def postsetup_input_port(self, n, d):
        self.setup_ordinal_port(self.input[n], d)
        if d != {}:
            raise AttributeError('Unknown keys: ' + str([*d.keys()]))

    def presetup_output_port(self, n, d):
        max_outputs = component_info[self.component]['outputs']
        if n >= max_outputs:
            raise KeyError('Component ' + self.component + ' do not have ' +
                    'output port ' + str(n))

    def postsetup_output_port(self, n, d):
        self.setup_ordinal_port(self.output[n], d)
        if d != {}:
            raise AttributeError('Unknown keys: ' + str([*d.keys()]))

    # ComponentBaseClass print functions

    def print_decl(self, cls):
        print('static MMAL_COMPONENT_T *cp_%s = NULL;' % self.name)
        for idx in range(len(self.output)):
            from_port = self.output[idx]
            if len(from_port) == 0:
                continue
            to_component = cls[from_port['connect_to']['name']]
            print('static MMAL_CONNECTION_T *conn_%s_%d_%s_%d = NULL;' % (
                self.name, idx,
                to_component.name, from_port['connect_to']['idx']))

    def print_init_component(self):
        print('\tcheck_mmal(mmal_component_create("%s", &cp_%s));' % (
                self.component, self.name))
        print('\tcheck_mmal(mmal_port_enable(cp_%s->control, cb_nop));' % (
                self.name))

    def print_finl_component(self):
        print('\tcheck_mmal(mmal_component_disable(cp_%s));' % self.name)
        print('\tcheck_mmal(mmal_component_destroy(cp_%s));' % self.name)
        print('\tcp_%s = NULL;' % self.name)

    def print_init_connection(self, cls):
        for idx in range(len(self.output)):
            from_port = self.output[idx]
            if not 'connect_to' in from_port:
                continue
            to_component = cls[from_port['connect_to']['name']]
            from_name = self.name
            from_idx = idx
            to_name = to_component.name
            to_idx = from_port['connect_to']['idx']
            conn = 'conn_%s_%d_%s_%d' % (from_name, from_idx, to_name, to_idx)
            print('\tcheck_mmal(mmal_connection_create(' + \
                    '&%s, cp_%s->output[%d], cp_%s->input[%d], %s));' % (
                            conn, from_name, from_idx, to_name, to_idx,
                            'MMAL_CONNECTION_FLAG_TUNNELLING'))
            print('\tcheck_mmal(mmal_connection_enable(%s));' % conn)

    def print_finl_connection(self, cls):
        for idx in range(len(self.output)):
            from_port = self.output[idx]
            if not 'connect_to' in from_port:
                continue
            to_component = cls[from_port['connect_to']['name']]
            from_name = self.name
            from_idx = idx
            to_name = to_component.name
            to_idx = from_port['connect_to']['idx']
            conn = 'conn_%s_%d_%s_%d' % (from_name, from_idx, to_name, to_idx)
            print('\tcheck_mmal(mmal_connection_disable(%s));' % conn)
            print('\tcheck_mmal(mmal_connection_destroy(%s));' % conn)
            print('\t%s = NULL;' % conn)


class ImageComponentClass(ComponentBaseClass):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_control_port(self, d):
        for key in list(d.keys()):
            if key == 'camera_num' and self.component in ['vc.ril.camera']:
                self.camera_num = d.pop(key)
        super().setup_control_port(d)

    def setup_ordinal_image_port(self, port, d0):
        for k0 in list(d0.keys()):
            if   k0 == 'width':
                port['width'] = int(d0.pop(k0))
            elif k0 == 'height':
                port['height'] = int(d0.pop(k0))
            elif k0 == 'encoding':
                port['encoding'] = mmal_encoding_short_to_full(d0.pop(k0))

    def setup_input_port(self, n, d0):
        super().presetup_input_port(n, d0)
        port = self.input[n]
        self.setup_ordinal_image_port(port, d0)
        for k0 in list(d0.keys()):
            if   k0 == 'rect' and self.component in ['vc.ril.video_render']:
                d1 = d0.pop(k0)
                rect = {}
                for k1 in list(d1.keys()):
                    if   k1 == 'x':
                        rect['x'] = int(d1.pop(k1))
                    elif k1 == 'y':
                        rect['y'] = int(d1.pop(k1))
                    elif k1 == 'width':
                        rect['width'] = int(d1.pop(k1))
                    elif k1 == 'height':
                        rect['height'] = int(d1.pop(k1))
                    else:
                        raise KeyError('Unknown key: rect.' + k1)
                port['rect'] = rect
            elif k0 == 'fullscreen' and \
                    self.component in ['vc.ril.video_render']:
                port['fullscreen'] = int(d0.pop(k0))
        super().postsetup_input_port(n, d0)

    def setup_output_port(self, n, d0):
        super().presetup_output_port(n, d0)
        port = self.output[n]
        self.setup_ordinal_image_port(port, d0)
        for k0 in list(d0.keys()):
            if k0 == 'source_pattern' and self.component in ['vc.ril.source']:
                port['source_pattern'] = d0.pop(k0)
        super().postsetup_output_port(n, d0)

    # ImageComponentClass print functions

    def print_init_ordinal_image_port(self, port, port_name):
        print('\tcheck_mmal(set_port_format(cp_%s, %s, %d, %d));' % (
                port_name, port['encoding'], port['width'], port['height']))

    def print_init_input_port(self, n):
        port = self.input[n]

        component_name = self.name
        port_name = '%s->input[%d]' % (component_name, n)

        self.print_init_ordinal_image_port(port, port_name)
        if 'rect' in port.keys() and 'fullscreen' in port.keys():
            raise KeyError('vc.ril.video_render: ' +
                    'rect and fullscreen are exclusive')
        elif 'rect' in port.keys():
            rect = port['rect']
            print('\tcheck_mmal(set_port_displayregion_rect(' +
                    'cp_%s, %d, %d, %d, %d));' % (port_name,
                            rect['x'], rect['y'],
                            rect['width'], rect['height']))
        elif 'fullscreen' in port.keys():
            print('\tcheck_mmal(set_port_displayregion_fullscreen(' +
                    'cp_%s, %d));' % (port_name, port['fullscreen']))
        print('\tcheck_mmal(mmal_component_enable(cp_%s));' % self.name)

    def print_init_output_port(self, n):
        port = self.output[n]

        component_name = self.name
        port_name = '%s->output[%d]' % (component_name, n)

        self.print_init_ordinal_image_port(port, port_name)
        if 'source_pattern' in port.keys():
            source_pattern = mmal_video_source_pattern_short_to_full(port['source_pattern'])
            print('\tcheck_mmal(set_port_video_source_pattern(' +
                    'cp_%s, %s, 0xdeadbeaf));' % (port_name, source_pattern))


def do_in_port_bp(from_port, to_port, attr):
    do_next = False
    if attr in to_port.keys():
        if from_port[attr] != to_port[attr]:
            raise RuntimeError(attr + ': ' + \
                    str(from_port[attr]) + ' vs. ' + str(to_port[attr]))
    else:
        to_port[attr] = from_port[attr]
        to_port['is_root'] = True
        do_next = True
    return do_next

# Forward-propagates width, height and encoding
def forward_propagate_format(cls):

    for cl in cls.values():
        if not cl.component in ['vc.ril.camera', 'vc.ril.rawcam',
                'vc.ril.source']:
            continue

        for from_port in cl.output:
            if not 'connect_to' in from_port:
                continue

            to_component = cls[from_port['connect_to']['name']]
            to_port = to_component.input[from_port['connect_to']['idx']]

            if not 'encoding' in from_port.keys():
                if 'encoding' in to_port.keys():
                    from_port['encoding'] = to_port['encoding']
                else:
                    from_port['encoding'] = 'MMAL_ENCODING_OPAQUE'

            do_in_port_bp(from_port, to_port, 'width')
            do_in_port_bp(from_port, to_port, 'height')
            do_in_port_bp(from_port, to_port, 'encoding')

    while True:
        do_next = False
        for cl in cls.values():

            for port in cl.input:
                # I'm talking about the root ports
                if not 'is_root' in port.keys():
                    continue
                # Different sizes and encodings on input/output ports
                elif cl.component in ['vc.ril.isp']:
                    continue
                # Different size but the same encoding
                elif cl.component in ['vc.ril.resize']:
                    do_next |= do_backpropagate(port, cl.output[0], 'encoding')
                # Same size and encoding
                else:
                    # This loop is for splitter
                    for to_port in cl.output:
                        do_next |= do_in_port_bp(prot, to_port, 'width')
                        do_next |= do_in_port_bp(port, to_port, 'height')
                        do_next |= do_in_port_bp(port, to_port, 'encoding')

            for port in cl.output:
                # I'm talking about the root ports
                if not 'is_root' in port.keys():
                    continue
                # Terminators
                elif cl.component in ['vc.ril.null_sink',
                        'vc.ril.video_render']:
                    continue

                to_component = cls[port['connect_to']['name']]
                to_port = to_component.input[port['connect_to']['idx']]

                # As for connection, size and encoding are the same on ports.
                do_next |= do_in_port_bp(port, to_port, 'width')
                do_next |= do_in_port_bp(port, to_port, 'height')
                do_next |= do_in_port_bp(port, to_port, 'encoding')

        if not do_next:
            break

def back_propagate_format(cls):

    def cls_append_connect_from(cls):
        for cl in cls.values():
            for idx in range(len(cl.output)):
                port = cl.output[idx]
                if not 'connect_to' in port.keys():
                    continue
                to_component = cls[port['connect_to']['name']]
                to_port = to_component.input[port['connect_to']['idx']]
                to_port['connect_from'] = {
                        'name': cl.name,
                        'idx': idx,
                }

    cls_append_connect_from(cls)

    for cl in cls.values():
        if not cl.component in ['vc.ril.null_sink', 'vc.ril.video_render']:
            continue

        dst_port = cl.input[0]
        src_component = cls[dst_port['connect_from']['name']]
        src_port = src_component.output[dst_port['connect_from']['idx']]

        if not 'encoding' in dst_port.keys():
            if 'encoding' in src_port.keys():
                dst_port['encoding'] = src_port['encoding']
            else:
                dst_port['encoding'] = 'MMAL_ENCODING_OPAQUE'

        do_in_port_bp(dst_port, src_port, 'width')
        do_in_port_bp(dst_port, src_port, 'height')
        do_in_port_bp(dst_port, src_port, 'encoding')

    while True:
        do_next = False
        for cl in cls.values():

            for port in cl.output:
                # I'm talking about the root ports
                if not 'is_root' in port.keys():
                    continue
                # Different sizes and encodings on input/output ports
                elif cl.component in ['vc.ril.isp']:
                    continue
                # Different size but the same encoding
                elif cl.component in ['vc.ril.resize']:
                    do_next |= do_backpropagate(port, cl.input[0], 'encoding')
                # Same size and encoding
                else:
                    dst_port = cl.input[0]
                    do_next |= do_in_port_bp(port, dst_port, 'width')
                    do_next |= do_in_port_bp(port, dst_port, 'height')
                    do_next |= do_in_port_bp(port, dst_port, 'encoding')

            for port in cl.input:
                # I'm talking about the root ports
                if not 'is_root' in port.keys():
                    continue
                # Initiators
                elif cl.component in ['vc.ril.camera', 'vc.ril.rawcam',
                        'vc.ril.source']:
                    continue

                src_component = cls[port['connect_from']['name']]
                src_port = src_component.output[port['connect_from']['idx']]

                # As for connection, size and encoding are the same on ports.
                do_next |= do_in_port_bp(port, src_port, 'width')
                do_next |= do_in_port_bp(port, src_port, 'height')
                do_next |= do_in_port_bp(port, src_port, 'encoding')

        if not do_next:
            break

def propagate_format(cls):
    cls1 = cls.copy()
    forward_propagate_format(cls1)
    cls2 = cls.copy()
    back_propagate_format(cls2)

    def merge_cls_format(cls, cls1, cls2):
        def merge_port_format(port, port1, port2, attr):
            in1 = attr in port1.keys()
            in2 = attr in port2.keys()
            if in1 and in2:
                if port1[attr] != port2[attr]:
                    raise RuntimeError('kkk')
                port[attr] = port1[attr]
            elif in1 and not in2:
                port[attr] = port1[attr]
            elif not in1 and in2:
                port[attr] = port2[attr]
            else: # not in1 and not in2
                raise RuntimeError('Cannot propagate attr ' + attr)

        for name in cls.keys():
            for i in range(len(cls[name].input)):
                port = cls[name].input[i]
                port1 = cls1[name].input[i]
                port2 = cls2[name].input[i]
                if len(port1) == 0 and len(port2) == 0:
                    continue
                merge_port_format(port, port1, port2, 'width')
                merge_port_format(port, port1, port2, 'height')
                merge_port_format(port, port1, port2, 'encoding')
            for i in range(len(cls[name].output)):
                port = cls[name].output[i]
                port1 = cls1[name].output[i]
                port2 = cls2[name].output[i]
                if len(port1) == 0 and len(port2) == 0:
                    continue
                merge_port_format(port, port1, port2, 'width')
                merge_port_format(port, port1, port2, 'height')
                merge_port_format(port, port1, port2, 'encoding')

    merge_cls_format(cls, cls1, cls2)

def main():

    dct = json.load(sys.stdin)

    cls = {}
    for name in dct.keys():
        data = dct[name]
        cl = ImageComponentClass(name, data.pop('component'))
        for port in list(data.keys()):
            if   port == 'control':
                cl.setup_control_port(data.pop('control'))
            elif port.startswith('input'):
                cl.setup_input_port(int(port[5:]), data.pop(port))
            elif port.startswith('output'):
                cl.setup_output_port(int(port[6:]), data.pop(port))
            else:
                raise IndexError('Unknown port name: ' + port)
        cls[name] = cl

    propagate_format(cls)

    print('#include "genmmal_internal.h"')
    print()
    for cl in cls.values():
        cl.print_decl(cls)
    print()
    print('int genmmal_init(void)')
    print('{')
    for cl in cls.values():
        cl.print_init_component()
    print()
    for cl in cls.values():
        if hasattr(cl, 'input'):
            for i in range(len(cl.input)):
                if len(cl.input[i]) != 0:
                    cl.print_init_input_port(i)
        if hasattr(cl, 'output'):
            for i in range(len(cl.output)):
                if len(cl.output[i]) != 0:
                    cl.print_init_output_port(i)
    print()
    for cl in cls.values():
        cl.print_init_connection(cls)
    print()
    print('\treturn 0;')
    print('}')
    print()

    print('int genmmal_finl(void)')
    print('{')
    for cl in cls.values():
        cl.print_finl_connection(cls)
    print()
    for cl in cls.values():
        cl.print_finl_component()
    print()
    print('\treturn 0;')
    print('}')

if __name__ == '__main__':
    main()
