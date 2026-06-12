#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cfg Template Module
Contains template for config implementation file
"""
from datetime import datetime


def get_cfg_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for config implementation file"""
    current_year = datetime.now().year
    current_time = datetime.now().strftime("%H:%M")
    return f'''/***********************************************************************************************************************
**--------------------------------------------------------------------------------------------------------------------**
** Copyright (c) {current_year} by G-Pulse.		All rights reserved.
** This software is copyright protected and proprietary to G-Pulse.
** G-Pulse grants to you only those rights as set out in the license conditions.
** All other rights remain with G-Pulse.
**--------------------------------------------------------------------------------------------------------------------**
**
* Administrative Information
* $Namespace_: ..\\ {module_name}$
* $Class_____: C$
* $Name______: {module_name}_Cfg.c$
* $ArchiVer__: 1$
* $FcVeri____: 1.0.0$
* $TemplateVer: {template_version}$
* $Author____: {author_name}$
*
* $Configuration or generate Date,Time: {current_time} {date} $
*
**--------------------------------------------------------------------------------------------------------------------**
** MAY BE CHANGED BY USER [Yes/No]: Yes
**--------------------------------------------------------------------------------------------------------------------**
** DESCRIPTION:
**
** {module_name} CFG data source file
**
***********************************************************************************************************************/

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "{module_name}_CfgData.h"

/***********************************************************************************************************************
**                        				Macro Definition                        								      **
***********************************************************************************************************************/

/***********************************************************************************************************************
**										Static Local Variables Definition											  **
***********************************************************************************************************************/
#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
#include "{module_name}_MemMap.h"

{module_name.upper()}_STATIC_	{module_name}_VolDiagCfgType	{module_name}_cfgVolDiag_lcatst[{module_name.upper()}_CFG_VOL_DIAG_TAB_LEN] =
{{
	{{
		1000.0F, 5.0F,
	}},
	{{
		2000.0F, 20.0F,
	}},
	{{
		3000.0F, 40.0F,
	}},
	{{
		4000.0F, 60.0F,
	}},
	{{
		5000.0F, 80.0F,
	}},
}};

#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
**										Global Variables Definition													  **
***********************************************************************************************************************/
#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
#include "{module_name}_MemMap.h"

const	{module_name}_CfgType	{module_name}_cfgCont_vcatst[{module_name.upper()}_CFG_VOL_SIG_NUM] =
{{
	{{
		{{
			&{module_name}_cfgVolDiag_lcatst[0U],
		}},
		(uint32*){module_name.upper()}_NULL_PTR, 10U, TRUE,
	}},
	{{
		{{
			&{module_name}_cfgVolDiag_lcatst[2U],
		}},
		(uint32*){module_name.upper()}_NULL_PTR, 20U, FALSE,
	}},
}};

#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
* $ArchiVer History:$
V1:
initial version for {module_name}.
realize interface description and requirement of memory section.
***********************************************************************************************************************/

/***********************************************************************************************************************
* $FcVer History:$
1.0.0	{date}	{author_name}
initial code version for V1 architecture.
realize function description.
***********************************************************************************************************************/
'''