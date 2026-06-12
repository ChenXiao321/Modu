#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Callout Header Template Module
Contains template for callout header file
"""
from datetime import datetime


def get_callout_header_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for callout header file"""
    current_year = datetime.now().year
    current_time = datetime.now().strftime("%H:%M")
    return f'''/***********************************************************************************************************************
**--------------------------------------------------------------------------------------------------------------------**
** Copyright (c)  {current_year} by G-Pulse.		All rights reserved.
** This software is copyright protected and proprietary to G-Pulse.
** G-Pulse grants to you only those rights as set out in the license conditions.
** All other rights remain with G-Pulse.
**--------------------------------------------------------------------------------------------------------------------**
**
* Administrative Information
* $Namespace_: ..\\ {module_name}$
* $Class_____: C$
* $Name______: {module_name}_Callout.h$
* $ArchiVer__: 1$
* $FcVeri____: 1.0.0$
* $TemplateVer: {template_version}$
* $Author____: {author_name}$
*
* $Configuration or generate Date,Time: {current_time} {date} $
*
**--------------------------------------------------------------------------------------------------------------------**
** MAY BE CHANGED BY USER [Yes/No]: No
**--------------------------------------------------------------------------------------------------------------------**
** DESCRIPTION:
**
** {module_name} Callout header file
**
***********************************************************************************************************************/
#ifndef {module_name.upper()}_CALLOUT_H_
#define {module_name.upper()}_CALLOUT_H_

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "{module_name}_Types.h"
/*other FC header file inclusion if necessary*/

/***********************************************************************************************************************
**										Global Function Prototypes													  **
***********************************************************************************************************************/
#define {module_name.upper()}_CODE_START
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
** Function Name	: {module_name}_CalloutInit
** Service ID		: None
** Sync/Async		: Synchronous
** Reentrancy		: Non_Reentrancy
** Parameter[in]	: None
** Parameter[inout]	: None
** Parameter[out]	: None
** Return Value		: boolean - TRUE/FALSE
** Description		: initialize callout function for special application requirement.
***********************************************************************************************************************/
extern	boolean	{module_name}_CalloutInit(void);

#define {module_name.upper()}_CODE_STOP
#include "{module_name}_MemMap.h"

#endif /* {module_name.upper()}_CALLOUT_H_ */

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