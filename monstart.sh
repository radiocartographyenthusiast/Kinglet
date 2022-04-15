#!/usr/bin/env bash
iw phy "$(iw phy | head -1 | cut -d" " -f2)" interface add mon0 type monitor && ifconfig mon0 up
