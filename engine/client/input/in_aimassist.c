/*
in_aimassist.c - gamepad aim assist target finder (Xbox build)
Copyright (C) 2026 HavocMasterChief

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

Single player only: the game runs a local server in the same process,
so the best target can be read straight from the server's entities.
The game DLL (hlsdk-portable-xbox, CBaseMonster::MonsterThink) marks
monsters that are hostile to the player with AIMASSIST_HOSTILE in
pev->iuser4, so friendly scientists and guards are never targeted.

The assist itself (slowdown, magnet, strafe follow, breakout and
escape) is in in_joy.c, ported from RealRTCWX's CL_JoystickMove.
*/

#include "common.h"
#include "client.h"
#include "server.h"

#if XASH_UWP

#define AIMASSIST_HOSTILE 0x4141 // 'AA', set by the game DLL

// lock cone: a sphere this many units around the target's chest,
// clamped so close targets don't get a huge cone and far ones a tiny one
#define AA_TARGET_RADIUS 40.0f
#define AA_MIN_CONE      2.5f  // degrees
#define AA_MAX_CONE      12.0f // degrees
#define AA_MAX_DIST      3000.0f

static float AA_AngleDelta( float a, float b )
{
	float d = a - b;

	while( d > 180.0f ) d -= 360.0f;
	while( d < -180.0f ) d += 360.0f;

	return d;
}

/*
===============
AimAssist_FindTarget

Returns lock strength 0..1 (0 = no target) and the yaw/pitch, in degrees,
that would put the crosshair on the best target's chest. Pitch follows the
engine convention: positive looks down.
===============
*/
float AimAssist_FindTarget( const vec3_t viewangles, float *dyaw, float *dpitch )
{
	edict_t *player;
	vec3_t eye;
	float best = 0.0f;
	int i;

	*dyaw = *dpitch = 0.0f;

	if( !SV_Active( ) || svs.maxclients != 1 || !svgame.edicts )
		return 0.0f;

	player = SV_EdictNum( 1 );
	if( !SV_IsValidEdict( player ) || player->v.health <= 0 )
		return 0.0f;

	VectorAdd( player->v.origin, player->v.view_ofs, eye );

	for( i = svs.maxclients + 1; i < svgame.numEntities; i++ )
	{
		edict_t *ent = SV_EdictNum( i );
		vec3_t chest, dir;
		float dist, horiz, yaw, pitch, ey, ep, err, cone, strength;
		trace_t tr;

		if( !ent || ent->free || ent->v.iuser4 != AIMASSIST_HOSTILE )
			continue;

		if( !FBitSet( ent->v.flags, FL_MONSTER ) || ent->v.deadflag != DEAD_NO || ent->v.health <= 0 || ent->v.takedamage == DAMAGE_NO )
			continue;

		if( FBitSet( ent->v.effects, EF_NODRAW ))
			continue;

		// aim a bit above the middle of the bounding box: chest height on humans
		VectorAverage( ent->v.absmin, ent->v.absmax, chest );
		chest[2] += ( ent->v.absmax[2] - ent->v.absmin[2] ) * 0.15f;

		VectorSubtract( chest, eye, dir );
		dist = VectorLength( dir );
		if( dist < 1.0f || dist > AA_MAX_DIST )
			continue;

		horiz = sqrt( dir[0] * dir[0] + dir[1] * dir[1] );
		yaw = RAD2DEG( atan2( dir[1], dir[0] ));
		pitch = -RAD2DEG( atan2( dir[2], horiz )); // engine pitch: down is positive

		ey = AA_AngleDelta( yaw, viewangles[YAW] );
		ep = AA_AngleDelta( pitch, viewangles[PITCH] );
		err = sqrt( ey * ey + ep * ep );

		cone = RAD2DEG( atan2( AA_TARGET_RADIUS, dist ));
		cone = bound( AA_MIN_CONE, cone, AA_MAX_CONE );
		if( err >= cone )
			continue;

		// strongest right on the target, fading to the cone edge and with distance
		strength = 1.0f - err / cone;
		if( dist > AA_MAX_DIST * 0.5f )
			strength *= 1.0f - ( dist - AA_MAX_DIST * 0.5f ) / ( AA_MAX_DIST * 0.5f );

		if( strength <= best )
			continue;

		// only targets the player can actually see
		tr = SV_Move( eye, vec3_origin, vec3_origin, chest, MOVE_NOMONSTERS, player, false );
		if( tr.fraction < 1.0f && tr.ent != ent )
			continue;

		best = strength;
		*dyaw = ey;
		*dpitch = ep;
	}

	return best;
}

#endif // XASH_UWP
