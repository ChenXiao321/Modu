#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C Source Template Module
Contains template for .c source file
"""

from datetime import datetime


def get_c_source_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for .c source file"""
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
* $Name______: {module_name}.c$
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
** {module_name} source file
**
***********************************************************************************************************************/

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "{module_name}.h"
#include "{module_name}_Callout.h"

/***********************************************************************************************************************
**							External Interface Function Pointers (for unit test mocking)							  **/
***********************************************************************************************************************/
Std_ReturnType (*McSpiReadFn)(uint8 channel, uint8* data, uint16 length) = NULL_PTR;
Std_ReturnType (*McCanWriteFn)(uint8 hth, const Can_PduType* pduInfo) = NULL_PTR;

/***********************************************************************************************************************
**							ASIL Safety Mechanism Access Layer														  **
***********************************************************************************************************************/
#define WDG_REFRESH()                                   WdgM_RefreshTrigger()
#define SAFETY_MONITOR(condition, errorId)              ((condition) ? (void)0 : SafetyMonitor_ReportError(errorId))
#define REDUNDANCY_CHECK(valueA, valueB, tolerance)     (((valueA) >= (valueB) - (tolerance)) && ((valueA) <= (valueB) + (tolerance)))

#define	{module_name.upper()}_REG_A_BIT2_7_POSITION			((uint8)2U)
#define	{module_name.upper()}_REG_A_BIT2_7_MASK				((uint16)0x00FCU)

/***********************************************************************************************************************
**										Static Local Variables Definition											  **
***********************************************************************************************************************/
/*$LV-B$*/
#define {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_START
#include "{module_name}_MemMap.h"

/*code line feed style of long variable definition*/
/*complex signal local implement runtime buffer*/
{module_name.upper()}_STATIC_	{module_name}_ComplexSignalLocalImplType \\
	{module_name}_bufComplexSignalLocalImpl_latst[{module_name.upper()}_SIG_BUF_LEN];

#define {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_STOP
#include "{module_name}_MemMap.h"
/*$LV-E$*/

/***********************************************************************************************************************
**										Static Local Function Declaration											  **
***********************************************************************************************************************/
#define {module_name.upper()}_CODE_START
#include "{module_name}_MemMap.h"

{module_name.upper()}_STATIC_	boolean	{module_name}_CheckArgIn(uint16 ChkId_u16, uint32 ChkCore_u32, uint8* ChkArgIn_pu8);

#define {module_name.upper()}_CODE_STOP
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
**										Function Source Code														  **
***********************************************************************************************************************/
#define {module_name.upper()}_CODE_START
#include "{module_name}_MemMap.h"

/***********************************************************************************************************************
** Function Name	: {module_name}_CheckArgIn
** Service ID		: None
** Sync/Async		: Synchronous
** Reentrancy		: Non_Reentrancy
** Parameter[in]	: uint16 ChkId_u16 - signal ID 0~0xFFFF
** Parameter[in]	: uint32 ChkCore_u32 - Core ID 0~5
** Parameter[in]	: uint8* ChkArgIn_pu8 - pointer to buffer of output argument
** Parameter[inout]	: None
** Parameter[out]	: None
** Return Value		: boolean - TRUE/FALSE
** Description		: {module_name} check argument input.
the function will check if the argument is valid.
***********************************************************************************************************************/
{module_name.upper()}_STATIC_	boolean	{module_name}_CheckArgIn(uint16 ChkId_u16, uint32 ChkCore_u32, uint8* ChkArgIn_pu8)
{{
	boolean	ErrFlag_b = FALSE;

	return (ErrFlag_b);
}}

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
void	{module_name}_Init(void)
{{
	boolean	ConditionA_b = FALSE;
	boolean	ConditionB_b = FALSE;
	boolean	ConditionC_b = FALSE;
	uint32	Cnt_u32 = 0U;
	uint16	RegA_u16 = 0U;
	uint16	BitField2_7_u16 = 0U;
	
	/*middle code will change ConditionA_b and Cnt_u32 value*/

	/*code style of if-else statement*/
	if (ConditionA_b == TRUE)
	{{
		if (Cnt_u32 > 0U)
		{{
			/*branch 1 code*/
		}}
		else
		{{
			/*branch 2 code*/
		}}
	}}
	else
	{{
		/*branch 3 code*/
	}}

	/*middle code will change ConditionA_b, ConditionB_b, ConditionC_b and Cnt_u32 value.*/

	/*code line feed style of multiple relational operators or logical operators statements*/
	if (((ConditionA_b == TRUE) && (ConditionB_b == TRUE)) || \\
		(ConditionC_b == TRUE) || \\
		(Cnt_u32 > {module_name.upper()}_SIG_BUF_LEN))
	{{
		/*branch 1 code*/
	}}
	else
	{{
		/*branch 2 code*/
	}}
	
	/*code style of bit-field operation*/
	/*RegA_u16 has got value from preceding code, and then get the value of bit-field 2~7*/
	BitField2_7_u16 = RegA_u16 & {module_name.upper()}_REG_A_BIT2_7_MASK;
	BitField2_7_u16 = BitField2_7_u16 >> {module_name.upper()}_REG_A_BIT2_7_POSITION;
	
	/*set the value of bit-field 2~7, and then write bit-field 2~7 back to RegA_u16*/
	BitField2_7_u16 = 0x0012U;
	BitField2_7_u16 = BitField2_7_u16 << {module_name.upper()}_REG_A_BIT2_7_POSITION;
	BitField2_7_u16 = BitField2_7_u16 & {module_name.upper()}_REG_A_BIT2_7_MASK;
	RegA_u16 = RegA_u16 & (~{module_name.upper()}_REG_A_BIT2_7_MASK);
	RegA_u16 = RegA_u16 | BitField2_7_u16;
}}

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
/*code line feed style of function which has multiple parameters*/
Std_ReturnType	{module_name}_FunctionDescription
(
	uint16 Id_u16,
	uint32 Parameter1Description_u32,
	uint32* Parameter2Description_pu32
)
{{
	Std_ReturnType Ret_t = E_NOT_OK;
	{module_name}_ComplexSignalLocalImplType*	Buf_ptst = &{module_name}_bufComplexSignalLocalImpl_latst[0U];
	uint32	Cnt_u32 = 0U;
	boolean	WaitFlag1_b = TRUE;
	boolean	WaitFlag2_b = TRUE;
	boolean	ErrFlag_b = FALSE;

	/*preprocessor directives should align to left and comment the #if content after #endif*/
#if ({module_name.upper()}_CFG_DEV_ERROR_DETECT == STD_ON)
	/*code line feed style of function calling which has multiple parameters*/
	ErrFlag_b = {module_name}_CheckArgIn
	(
		Id_u16,
		Parameter1Description_u32,
		(uint8*)Parameter2Description_pu32
	);
	
#if ({module_name.upper()}_CFG_ERROR_RECORD == STD_ON)
	Buf_ptst[0U].FuncCompl_b = ErrFlag_b;
#endif	/*#if ({module_name.upper()}_CFG_ERROR_RECORD == STD_ON)*/
#endif	/*#if ({module_name.upper()}_CFG_DEV_ERROR_DETECT == STD_ON)*/

	/*code style of for statement*/
	for (Cnt_u32 = 0U; Cnt_u32 < (uint32){module_name.upper()}_SIG_BUF_LEN; Cnt_u32++)
	{{
		/*loop code*/
	}}

	/*code style of while statement*/
	while (WaitFlag1_b == TRUE)
	{{
		/*loop code will change WaitFlag1 value*/
		WaitFlag1_b = FALSE;
	}}
	
	/*code style of do-while statement*/
	do
	{{
		/*loop code will change WaitFlag2 value*/
		WaitFlag2_b = FALSE;
	}} while (WaitFlag2_b == TRUE);

	/*code style of switch-case statement*/
	switch (Buf_ptst[Cnt_u32].MainState_t)
	{{
		case {module_name}_MainState_Idle_e:
		{{
			/*idle case code*/
		}}
		break;
		case {module_name}_MainState_Init_e:
		{{
			/*initialization case code*/
		}}
		break;
		case {module_name}_MainState_Normal_e:
		{{
			/*normal case code*/
		}}
		break;
		case {module_name}_MainState_Fault_e:
		{{
			/*fault case code*/
		}}
		break;
		default:
		{{
			/*default case code*/
		}}
		break;
	}}
	
	return (Ret_t);
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
