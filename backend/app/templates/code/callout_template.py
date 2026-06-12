#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Callout Template Module
Contains template for callout implementation file
"""
from datetime import datetime


def get_callout_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for callout implementation file"""
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
* $Name______: {module_name}_Callout.c$
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
** {module_name} Callout source file
**
***********************************************************************************************************************/

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "{module_name}_Callout.h"
/*other FC header file inclusion if necessary*/

/***********************************************************************************************************************
**                        				Macro Definition                        								      **
***********************************************************************************************************************/

/***********************************************************************************************************************
**										Typedef Definition															  **
***********************************************************************************************************************/

/***********************************************************************************************************************
**										Static Local Variables Definition											  **
***********************************************************************************************************************/
#define {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_START
#include "{module_name}_MemMap.h"

#define {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_STOP
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
**										Static Local Function Declaration											  **
***********************************************************************************************************************/
#define {module_name.upper()}_CODE_START
#include "{module_name}_MemMap.h"

#define {module_name.upper()}_CODE_STOP
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
**										Function Source Code														  **
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
boolean	{module_name}_CalloutInit(void)
{{
	boolean FuncCompl_b = TRUE;

	return (FuncCompl_b);
}}


#define {module_name.upper()}_CODE_STOP
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
