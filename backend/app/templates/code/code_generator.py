#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code Generator Module
Contains functions for generating C code files based on templates
"""

import os
from datetime import datetime

from .c_template import get_c_source_content
from .cali_template import get_cali_content
from .callout_template import get_callout_content
from .callouth_template import get_callout_header_content
from .cfg_h_template import get_cfg_header_content
from .cfg_template import get_cfg_content
from .cfgdata_h_template import get_cfgdata_header_content
from .h_template import get_header_content
from .memmap_h_template import get_memmap_header_content
from .types_h_template import get_types_header_content


class CodeGenerator:
    def __init__(self):
        pass

    def generate_files(self, module_name, author_name, output_dir, template_version="1.0.0"):
        """Generate all files based on template files"""

        # Create output directory if not exists
        module_dir = os.path.join(output_dir, module_name)
        os.makedirs(module_dir, exist_ok=True)

        # Get current date for version info
        current_date = datetime.now().strftime("%d.%m.%Y")

        # Template files content (from the provided template)
        template_files = {
            f"{module_name}.c": get_c_source_content(module_name, author_name, current_date, template_version),
            f"{module_name}.h": get_header_content(module_name, author_name, current_date, template_version),
            f"{module_name}_Cali.c": get_cali_content(module_name, author_name, current_date, template_version),
            f"{module_name}_Callout.c": get_callout_content(module_name, author_name, current_date, template_version),
            f"{module_name}_Callout.h": get_callout_header_content(module_name, author_name, current_date, template_version),
            f"{module_name}_Cfg.c": get_cfg_content(module_name, author_name, current_date, template_version),
            f"{module_name}_Cfg.h": get_cfg_header_content(module_name, author_name, current_date, template_version),
            f"{module_name}_CfgData.h": get_cfgdata_header_content(module_name, author_name, current_date, template_version),
            f"{module_name}_MemMap.h": get_memmap_header_content(module_name, author_name, current_date, template_version),
            f"{module_name}_Types.h": get_types_header_content(module_name, author_name, current_date, template_version)
        }
        
        # Write all files
        for filename, content in template_files.items():
            filepath = os.path.join(module_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
