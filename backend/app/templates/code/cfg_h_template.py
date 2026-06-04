#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cfg Header Template Module
Contains template for config header file
"""
from datetime import datetime


def get_cfg_header_content(module_name, author_name, date):
    """Get content for config header file"""
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
* $Name______: {module_name}_Cfg.h$
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
** {module_name} CFG header file
**
***********************************************************************************************************************/
#ifndef {module_name.upper()}_CFG_H_
#define {module_name.upper()}_CFG_H_

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "Std_Types.h"
/*other FC header file inclusion if necessary*/

/***********************************************************************************************************************
**                        				Macro Definition                        								      **
***********************************************************************************************************************/

#define	{module_name.upper()}_CFG_VOL_SIG_NUM               ((uint8)2U)

#define	{module_name.upper()}_CFG_VOL_DIAG_TAB_LEN          ((uint8)5U)

#define	{module_name.upper()}_CFG_DEV_ERROR_DETECT          (STD_ON)
#define	{module_name.upper()}_CFG_ERROR_RECORD              (STD_ON)

#endif /* {module_name.upper()}_CFG_H_ */

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