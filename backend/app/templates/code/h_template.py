#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
H Header Template Module
Contains template for .h header file
"""

from datetime import datetime


def get_header_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for .h header file"""
    current_year = datetime.now().year
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
* $Name______: {module_name}.h$
* $ArchiVer__: 1$
* $FcVeri____: 1.0.0$
* $TemplateVer: {template_version}$
* $Author____: {author_name}$
**
**--------------------------------------------------------------------------------------------------------------------**
** MAY BE CHANGED BY USER [Yes/No]: No
**--------------------------------------------------------------------------------------------------------------------**
** DESCRIPTION:
**
** {module_name} header file
**
***********************************************************************************************************************/
#ifndef {module_name.upper()}_H_
#define {module_name.upper()}_H_

/***********************************************************************************************************************
**                        				Other Header File Inclusion                    								  **
***********************************************************************************************************************/
#include "{module_name}_CfgData.h"

/***********************************************************************************************************************
**										Global Function Prototypes													  **
***********************************************************************************************************************/
#define {module_name.upper()}_CODE_START
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
** Function Name    : {module_name}_Init
** Service ID       : None
** Sync/Async       : Synchronous
** Reentrancy       : Non_Reentrancy
** Parameter[in]    : None
** Parameter[inout]	: None
** Parameter[out]   : None
** Return Value     : void
** Description      : {module_name} initialization
the function will set initial value for all {module_name} variables.
***********************************************************************************************************************/
extern	void	{module_name}_Init(void);

/***********************************************************************************************************************
** Function Name	: {module_name}_FunctionDescription
** Service ID		: None
** Sync/Async		: Synchronous
** Reentrancy		: Non_Reentrancy
** Parameter[in]	: uint16 Id_u16 - signal ID 0~0xFFFF
** Parameter[in]	: uint32 Parameter1Description_u32 - Parameter1 0~0xFFFFFFFF
** Parameter[inout]	: None
** Parameter[out]	: uint32* Parameter2Description_pu32 - pointer to buffer of output data
** Return Value		: Std_ReturnType - E_OK/E_NOT_OK
** Description		: {module_name} provide demo interface.
interface function detail description.
***********************************************************************************************************************/
extern	Std_ReturnType	{module_name}_FunctionDescription
(
	uint16 Id_u16,
	uint32 Parameter1Description_u32,
	uint32* Parameter2Description_pu32
);

#define {module_name.upper()}_CODE_STOP
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
**                        External Interface Access Layer (for Mock testing)                                          **
***********************************************************************************************************************/
#define MCAL_SPI_READ(channel, data, length)          Spi_Read(channel, data, length)
#define MCAL_CAN_WRITE(hth, pduInfo)                  Can_Write(hth, pduInfo)
#define OS_SET_REL_ALARM(alarm, increment, cycle)     SetRelAlarm(alarm, increment, cycle)

/***********************************************************************************************************************
**                        ASIL Safety Mechanism Access Layer                                                          **
***********************************************************************************************************************/
#define WDG_REFRESH()                                   WdgM_RefreshTrigger()
#define SAFETY_MONITOR(condition, errorId)              ((condition) ? (void)0 : SafetyMonitor_ReportError(errorId))
#define REDUNDANCY_CHECK(valueA, valueB, tolerance)     (((valueA) >= (valueB) - (tolerance)) && ((valueA) <= (valueB) + (tolerance)))

#endif /* {module_name.upper()}_H_ */

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
