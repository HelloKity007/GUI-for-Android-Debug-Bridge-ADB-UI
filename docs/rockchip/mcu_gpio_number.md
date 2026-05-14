计算方法：

如MCU的IO是PA0-7, PB0-7, PC0-7, PD0-7，以此类推。

例如PA0的io，group是0， pin是0；PC5的io，group是2，pin是5，代入以下计算的宏中得出


计算宏定义：

#defineMCU_GRP_PIN(group, pin)        (((uint32_t)(group +1) <<16) + pin)

#defineMCUA_GROUP_BASE                ((uint8_t)0)        // GD32F310

#defineMCU_GPIO_MAP_INDEX_START           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 0)

//group A

#defineMCU_PA0           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 0)

#defineMCU_PA1           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 1)

#defineMCU_PA2           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 2)

#defineMCU_PA3           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 3)

#defineMCU_PA4           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 4)

#defineMCU_PA5           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 5)

#defineMCU_PA6           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 6)

#defineMCU_PA7           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 7)

#defineMCU_PA8           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 8)

#defineMCU_PA9           MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 9)

#defineMCU_PA10          MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 10)

#defineMCU_PA11          MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 11)

#defineMCU_PA12          MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 12)

#defineMCU_PA13          MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 13)

#defineMCU_PA14          MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 14)

#defineMCU_PA15          MCU_GRP_PIN((0+ MCUA_GROUP_BASE), 15)

//group B

#defineMCU_PB0           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 0)

#defineMCU_PB1           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 1)

#defineMCU_PB2           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 2)

#defineMCU_PB3           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 3)

#defineMCU_PB4           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 4)

#defineMCU_PB5           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 5)

#defineMCU_PB6           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 6)

#defineMCU_PB7           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 7)

#defineMCU_PB8           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 8)

#defineMCU_PB9           MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 9)

#defineMCU_PB10          MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 10)

#defineMCU_PB11          MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 11)

#defineMCU_PB12          MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 12)

#defineMCU_PB13          MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 13)

#defineMCU_PB14          MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 14)

#defineMCU_PB15          MCU_GRP_PIN((1+ MCUA_GROUP_BASE), 15)

//group C

#defineMCU_PC0           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 0)

#defineMCU_PC1           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 1)

#defineMCU_PC2           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 2)

#defineMCU_PC3           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 3)

#defineMCU_PC4           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 4)

#defineMCU_PC5           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 5)

#defineMCU_PC6           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 6)

#defineMCU_PC7           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 7)

#defineMCU_PC8           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 8)

#defineMCU_PC9           MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 9)

#defineMCU_PC10          MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 10)

#defineMCU_PC11          MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 11)

#defineMCU_PC12          MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 12)

#defineMCU_PC13          MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 13)

#defineMCU_PC14          MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 14)

#defineMCU_PC15          MCU_GRP_PIN((2+ MCUA_GROUP_BASE), 15)

//group D

#defineMCU_PD0           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),0)

#defineMCU_PD1           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),1)

#defineMCU_PD2           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),2)

#defineMCU_PD3           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),3)

#defineMCU_PD4           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),4)

#defineMCU_PD5           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),5)

#defineMCU_PD6           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),6)

#defineMCU_PD7           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),7)

#defineMCU_PD8           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),8)

#defineMCU_PD9           MCU_GRP_PIN((3+ MCUA_GROUP_BASE),9)

#defineMCU_PD10          MCU_GRP_PIN((3+ MCUA_GROUP_BASE),10)

#defineMCU_PD11          MCU_GRP_PIN((3+ MCUA_GROUP_BASE),11)

#defineMCU_PD12          MCU_GRP_PIN((3+ MCUA_GROUP_BASE),12)

#defineMCU_PD13          MCU_GRP_PIN((3+ MCUA_GROUP_BASE),13)

#defineMCU_PD14          MCU_GRP_PIN((3+ MCUA_GROUP_BASE),14)

#defineMCU_PD15          MCU_GRP_PIN((3+ MCUA_GROUP_BASE),15)

//group E

#defineMCU_PE0           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),0)

#defineMCU_PE1           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),1)

#defineMCU_PE2           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),2)

#defineMCU_PE3           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),3)

#defineMCU_PE4           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),4)

#defineMCU_PE5           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),5)

#defineMCU_PE6           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),6)

#defineMCU_PE7           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),7)

#defineMCU_PE8           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),8)

#defineMCU_PE9           MCU_GRP_PIN((4+ MCUA_GROUP_BASE),9)

#defineMCU_PE10          MCU_GRP_PIN((4+ MCUA_GROUP_BASE),10)

#defineMCU_PE11          MCU_GRP_PIN((4+ MCUA_GROUP_BASE),11)

#defineMCU_PE12          MCU_GRP_PIN((4+ MCUA_GROUP_BASE),12)

#defineMCU_PE13          MCU_GRP_PIN((4+ MCUA_GROUP_BASE),13)

#defineMCU_PE14          MCU_GRP_PIN((4+ MCUA_GROUP_BASE),14)

#defineMCU_PE15          MCU_GRP_PIN((4+ MCUA_GROUP_BASE),15)

//group f

#defineMCU_PF0           MCU_GRP_PIN((5+ MCUA_GROUP_BASE),0)

#defineMCU_PF1           MCU_GRP_PIN((5+ MCUA_GROUP_BASE),1)
