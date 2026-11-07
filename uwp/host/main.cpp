/*
main.cpp - UWP / Xbox Series Dev Mode host for Xash3D FWGS
Copyright (C) 2026 HavocMasterChief

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

The engine itself lives in xash.dll inside the app package. This host
only exists because a UWP app needs a CoreWindow entry point, which
SDL_winrt_main_NonXAML.cpp provides; SDL then calls main() below.

Game data is read from the app's LocalState folder, where the user
copies their Half-Life files into LocalState/HalfLife through the
Xbox Device Portal. Expansions get sibling folders (BlueShift, OpposingForce,
Decay) that fall back to HalfLife for shared content.
*/

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>

#include "SDL.h"
#include "SDL_main.h"

typedef void ( *pfnChangeGame )( const char *progname );
typedef int ( *pfnInit )( int argc, char **argv, const char *progname, int bChangeGame, pfnChangeGame func );

static void FatalError( const char *fmt, ... )
{
	char buf[1024];
	va_list args;

	va_start( args, fmt );
	vsnprintf( buf, sizeof( buf ), fmt, args );
	va_end( args );

	SDL_ShowSimpleMessageBox( SDL_MESSAGEBOX_ERROR, "Xash3D FWGS", buf, NULL );
}

int main( int argc, char *argv[] )
{
	// LocalState is the only writable place an app container gets.
	// Everything the engine reads or writes (valve/, config, saves, logs) goes there.
	const char *localState = SDL_WinRTGetFSPathUTF8( SDL_WINRT_PATH_LOCAL_FOLDER );

	if( !localState )
	{
		FatalError( "Can't determine LocalState folder: %s", SDL_GetError( ));
		return 1;
	}

	std::string basedir = std::string( "XASH3D_BASEDIR=" ) + localState;
	_putenv( basedir.c_str( ));

	// install folder is read-only, but the engine falls back to it for extras.pk3 etc.
	const char *installDir = SDL_WinRTGetFSPathUTF8( SDL_WINRT_PATH_INSTALLED_LOCATION );
	if( installDir )
	{
		std::string rodir = std::string( "XASH3D_RODIR=" ) + installDir;
		_putenv( rodir.c_str( ));
	}

	HMODULE engine = LoadPackagedLibrary( L"xash.dll", 0 );

	if( !engine )
	{
		FatalError( "Can't load xash.dll (error %lu)", GetLastError( ));
		return 1;
	}

	pfnInit Host_Main = (pfnInit)GetProcAddress( engine, "Host_Main" );

	if( !Host_Main )
	{
		FatalError( "xash.dll is missing the Host_Main export" );
		return 1;
	}

	// first boot: software renderer, developer console messages, engine.log in LocalState
	static char arg0[] = "xash3d";
	static char argDev[] = "-dev";
	static char argDevLevel[] = "2";
	static char argLog[] = "-log";
	static char argRef[] = "-ref";
	static char argRefName[] = "soft";
	static char *engineArgs[] = { arg0, argDev, argDevLevel, argLog, argRef, argRefName, NULL };

	(void)argc;
	(void)argv;

	// base game folder in LocalState (and in the package)
	return Host_Main( 6, engineArgs, "HalfLife", 0, NULL );
}
