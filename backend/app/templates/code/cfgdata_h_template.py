#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CfgData Header Template Module
Contains template for config data header file
"""
from datetime import datetime


def get_cfgdata_header_content(module_name, author_name, date):
    """Get content for config data header file"""
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
* $Name______: {module_name}_CfgData.h$
* $ArchiVer__: 1$
* $FcVeri____: 1.0.0$
* $Author____: {author_name}$
*
* $Configuration or generate Date,Time: {current_time} {date} $
*
**--------------------------------------------------------------------------------------------------------------------**
** MAY BE CHANGED BY USER [Yes/No]: Yes
**--------------------------------------------------------------------------------------------------------------------**
** DESCRIPTION:
**
** {module_name} CFG data header file
**
***********************************************************************************************************************/
#ifndef {module_name.upper()}_CFGDATA_H_
#define {module_name.upper()}_CFGDATA_H_

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "{module_name}_Types.h"
/*other FC header file inclusion if necessary*/

/***********************************************************************************************************************
**                        				Global Variables With Declaration											  **
***********************************************************************************************************************/
#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
#include "{module_name}_MemMap.h"

extern	const	{module_name}_CfgType	{module_name}_cfgCont_vcatst[{module_name.upper()}_CFG_VOL_SIG_NUM];

#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
#include "{module_name}_MemMap.h"

#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_START
#include "{module_name}_MemMap.h"

extern	const	{module_name}_VolCalcCaliType	{module_name}_facVolCalcCali_katst[{module_name.upper()}_CFG_VOL_SIG_NUM];

#define {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_STOP
#include "{module_name}_MemMap.h"

#endif /* {module_name.upper()}_CFGDATA_H_ */

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