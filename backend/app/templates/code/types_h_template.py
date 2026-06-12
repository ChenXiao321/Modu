#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Types Header Template Module
Contains template for types header file
"""

from datetime import datetime


def get_types_header_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for types header file"""
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
* $Name______: {module_name}_Types.h$
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
** {module_name} types header file
**
***********************************************************************************************************************/
#ifndef {module_name.upper()}_TYPES_H_
#define {module_name.upper()}_TYPES_H_

/***********************************************************************************************************************
**										Other Header File Inclusion													  **
***********************************************************************************************************************/
#include "{module_name}_Cfg.h"

/***********************************************************************************************************************
**                        				Macro Definition                        								      **
***********************************************************************************************************************/
#define {module_name.upper()}_UNUSED_PARAMETER(VariableName)	(void)(VariableName)
#define {module_name.upper()}_NULL_PTR							((void *) 0)

#ifndef {module_name.upper()}_INLINE_
#if defined __TASKING__
#define {module_name.upper()}_INLINE_		static inline
#elif defined __HIGHTEC__
#define {module_name.upper()}_INLINE_		static inline __attribute__	((always_inline))
#endif
#endif

#ifndef {module_name.upper()}_STATIC_
#define {module_name.upper()}_STATIC_		static
#endif

#define	{module_name.upper()}_SIG_BUF_LEN		((uint8)10U)

#define	{module_name.upper()}_TEMP				((sint16)20)

#define	{module_name.upper()}_VOL_GAIN			((float32)10.5F)
#define	{module_name.upper()}_VOL_OFFSET		((float32)2.0F)

/***********************************************************************************************************************
**										Typedef Definition															  **
***********************************************************************************************************************/

/*$TDB-B$*/
typedef	uint32	{module_name}_InputDataType;	/*specifies the input data type*/
/*$TDB-E$*/

/*$TDB-B$*/
typedef	uint8	{module_name}_InitStuType;	/*specifies the initialized status type*/
#define	{module_name.upper()}_INITSTU_UNDEF	(({module_name}_InitStuType)0x00U)	/*undefined status*/
#define	{module_name.upper()}_INITSTU_INIT_FAILED	(({module_name}_InitStuType)0x01U)	/*initialization failed*/
#define	{module_name.upper()}_INITSTU_INITED	(({module_name}_InitStuType)0x02U)	/*initialized*/
/*$TDB-E$*/

/*$TDE-B$*/
typedef	enum	{module_name}_MainState
{{
	{module_name}_MainState_Idle_e = 0U,	/*idle state*/
	{module_name}_MainState_Init_e = 1U,	/*initialization state*/
	{module_name}_MainState_Normal_e = 2U,	/*normal state*/
	{module_name}_MainState_Fault_e = 3U,	/*fault state*/
}}{module_name}_MainStateType;	/*specifies the main state type*/
/*$TDE-E$*/

/*$TDST-B$*/
typedef	struct	{module_name}_ComplexSignalLocalImpl
{{
	uint32*	OutputBufAddr_pu32;	/*pointer to output buffer*/
	float32	VolGain_f32;	/*voltage gain*/
	{module_name}_MainStateType	MainState_t;	/*main state*/
	uint32	InputData_u32;	/*input data*/
	uint16	ChkId_u16;	/*check ID*/
	boolean	FuncCompl_b;	/*function completed*/
}}{module_name}_ComplexSignalLocalImplType;	/*specifies the complex signal local implement*/
/*$TDST-E$*/

/*$TDST-B$*/
typedef	struct	{module_name}_VolDiagCfg
{{
	float32	VolUpperlim_f32;	/*voltage upper limit(unit V)*/
	float32	VolLowerLim_f32;	/*voltage lower limit(unit V)*/
}}{module_name}_VolDiagCfgType;	/*specifies the voltage diagnostic configuration*/
/*$TDST-E$*/

/*$TDST-B$*/
typedef	struct	{module_name}_Cfg
{{
	{module_name}_VolDiagCfgType*	VolDiag_cptst;	/*pointer to voltage diagnostic configuration*/
	uint32*	InputBufAddr_pu32;	/*pointer to input buffer*/
	uint16	LoopCntMax_u16;	/*loop counter maximum*/
	boolean	OptiFunc_b;	/*enable/disable optional function*/
}}{module_name}_CfgType;	/*specifies the configuration container*/
/*$TDST-E$*/

/*$TDST-B$*/
typedef	struct	{module_name}_VolCalcCali
{{
	float32	VolGain_f32;	/*voltage gain*/
	float32	VolOft_f32;	/*voltage offset*/
}}{module_name}_VolCalcCaliType;	/*specifies the voltage calculation calibration container*/
/*$TDST-E$*/

#endif /* {module_name.upper()}_TYPES_H_ */

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

