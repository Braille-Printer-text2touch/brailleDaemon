/****************************
 * stepperHat.c implements code to run the Adafruit motor hat in C.
 *
 * example compilation:
 *    gcc -o stepperHat stepperHat.c -l wiringPi
 ************/
#include <stdio.h>
#include <stdlib.h>
#include <wiringPiI2C.h>

#define HAT_ADDR 0x60

#define MODE_1_REG 0x00
#define MODE_2_REG 0x01
#define PRESCALE_REG 0xFE
#define PWM_REGS_BASE 0x06 // 16 registers start from here

#define PWM_FREQUENCY 1600.00

/*******************
 * motorHatReset() resets the control register of the hat
 *
 * @param fd: int, the file descriptor representing the hat I2C device
 *
 * @return: nothing
 **************/
void motorHatReset(int fd) {
  if (wiringPiI2CWriteReg8(fd, MODE_1_REG, 0x00) < 0) {
    fprintf(stderr, "Unable to write to register %d\n", MODE_1_REG);
    exit(-1);
  }
}

/*******************
 * motorHatSetup() handles the I2C logic to set up the hat
 *
 * @return: int, the file descriptor of the hat I2C device
 **************/
int motorHatSetup() {
  int fd = wiringPiI2CSetup(HAT_ADDR);
  if (fd < 0) {
    fprintf(stderr, "Unable to register at at %d\n", HAT_ADDR);
    exit(-1);
  }
  puts("Registered hat!");

  motorHatReset(fd);

  return fd;
}
