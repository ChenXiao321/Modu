#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MemMap Header Template Module
Contains template for memory mapping header file
"""
from datetime import datetime


def get_memmap_header_content(module_name, author_name, date, template_version="1.0.0"):
    """Get content for memory mapping header file"""
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
* $Name______: {module_name}_MemMap.h$
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
** {module_name} MemMap header file
**
***********************************************************************************************************************/
#ifndef {module_name.upper()}_MEMMAP_H_
#define {module_name.upper()}_MEMMAP_H_

/**
 * 									G-Pulse	memory layout standard
 *
 * 	Type		    Tasking		 		Hightec		Definition							Section
 *	.text		    code 				ax			_CODE_(START/STOP)					Code.(*).(*)
 * 	.bss_clear		farbss           	awB			CLEAR_FAR_DATA	                    ClearFarData.
 * 	.bss_noclear	farnoclear	        awB			NO_CLEAR_FAR_DATA	                NoClearFarData.
 *	.zbss_clear		nearbss             awBz		CLEAR_NEAR_DATA                 	ClearNearData.
 *  .zbss_noclear	nearnoclear         awBz		NO_CLEAR_NEAR_DATA	                NoClearNearData.
 *	.sbss		    a0bss				awBs		CLEAR_A0_DATA						ClearA0Data.
 *	.data		    fardata				aw			INIT_FAR_DATA						InitFarData.
 *	.zdata		    neardata			awz			INIT_NEAR_DATA						InitNearData.
 *	.sdata		    a0data				aws			INIT_A0_DATA						InitA0Data.
 *	.rodata		    farrom				a			CONST_FAR_DATA						ConstFarData.
 *	.zrodata	    nearrom				az			CONST_NEAR_DATA						ConstNearData.
 *	.rodata_a1 	    a1rom				as			CONST_A1_DATA						ConstA1Data.
 *
 **/

#define {module_name.upper()}_MEMMAP_ERROR		/*Make error for check*/

/*For compiler TASKING*/
#if defined __TASKING__
/************************************************* Data Section *******************************************************/

/**
 * !!!!NOTE!!!!:
 * 	attribute order:
 * 	start:	addressing mode - clear - align
 * 	stop:	align - addressing mode - clear
 */

#if defined {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_START
    #pragma section farbss "ClearFarData.Align4.{module_name}"
    #pragma default_near_size 0
    #pragma clear
    #pragma align 4
    #undef {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_STOP
    #pragma align restore
    #pragma clear restore
    #pragma default_near_size restore
    #pragma section farbss restore
    #undef {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
    #pragma section farrom "ConstFarData.Align4.{module_name}"
    #pragma default_near_size 0
    #pragma align 4
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
    #pragma align restore
    #pragma default_near_size restore
    #pragma section farrom restore
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_START
    #pragma section farrom "ConstFarData.Align4.Cali.{module_name}"
    #pragma default_near_size 0
    #pragma align 4
	#pragma protect on
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_STOP
	#pragma protect restore
    #pragma align restore
    #pragma default_near_size restore
    #pragma section farrom restore
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR

/************************************************* Code Section *******************************************************/
#elif defined {module_name.upper()}_CODE_START
    #pragma section code "Code.{module_name}"
    #undef {module_name.upper()}_CODE_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CODE_STOP
    #pragma section code restore
    #undef {module_name.upper()}_CODE_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR


/************************************************ Compiler optimize ***************************************************/
#elif defined {module_name.upper()}_COMPILER_OPTIMIZE_START
	#pragma optimize O2
	#pragma profiling off
	#pragma tradeoff 2
	#undef {module_name.upper()}_COMPILER_OPTIMIZE_START
	#undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_COMPILER_OPTIMIZE_STOP
	#pragma tradeoff restore
	#pragma profiling restore
	#pragma endoptimize
	#undef {module_name.upper()}_COMPILER_OPTIMIZE_STOP
	#undef {module_name.upper()}_MEMMAP_ERROR
 #endif
 
/*For compiler HIGHTEC*/
#elif defined __HIGHTEC__

/************************************************* Data Section *******************************************************/
#if defined {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_START
    #pragma section  "ClearFarData.Align4.{module_name}" awB 4
    #undef {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_STOP
    #pragma section 
    #undef {module_name.upper()}_CLEAR_FAR_DATA_ALIGN4_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
    #pragma section  "ConstFarData.Align4.{module_name}" a 4
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
    #pragma section 
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_START
    #pragma section  "ConstFarData.Align4.Cali.{module_name}" a 4
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_STOP
    #pragma section
    #undef {module_name.upper()}_CONST_FAR_DATA_ALIGN4_CALI_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR
/************************************************* Code Section *******************************************************/
#elif defined {module_name.upper()}_CODE_START
    #pragma section  "Code.{module_name}" ax
    #undef {module_name.upper()}_CODE_START
    #undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_CODE_STOP
    #pragma section 
    #undef {module_name.upper()}_CODE_STOP
    #undef {module_name.upper()}_MEMMAP_ERROR


/************************************************ Compiler optimize ***************************************************/
#elif defined {module_name.upper()}_COMPILER_OPTIMIZE_START
	#pragma GCC optimize ("-O2")
	#undef {module_name.upper()}_COMPILER_OPTIMIZE_START
	#undef {module_name.upper()}_MEMMAP_ERROR

#elif defined {module_name.upper()}_COMPLIER_OPTIMIZE_STOP
	#pragma GCC reset_options
	#undef {module_name.upper()}_COMPILER_OPTIMIZE_STOP
	#undef {module_name.upper()}_MEMMAP_ERROR
#endif
#endif	/*__TASKING__ or __HIGHTEC__*/


#if defined {module_name.upper()}_MEMMAP_ERROR
#error "!!! {module_name}_MemMap.h,Wrong pragma command !!!"
#endif

#undef {module_name.upper()}_MEMMAP_H_	/*Must be #undef here*/
#endif	/*{module_name.upper()}_MEMMAP_H_*/

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