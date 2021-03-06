
section reset
dd 0x2000f000 ; 0x0
dd 0x00000009 ; reset vector 0x4
global bsp_boot
global bsp_exit

BL bsp_boot  ; Branch to bsp boot // 0x8
BL bsp_exit  ; do exit stuff 0xc
local_loop:
BW local_loop ; 0x10
dd 0 ; 0x14
dd 0 ; 0x18
dd 0 ; 0x1c
dd 0 ; 0x20
dd 0 ; 0x24
dd 0 ; 0x28
dd 0 ; 0x2c
dd 0 ; 0x30
dd 0 ; 0x34
dd 0 ; 0x38
dd 0x00000041 ; 0x3c systick
global bsp_systick_isr
BW bsp_systick_isr
