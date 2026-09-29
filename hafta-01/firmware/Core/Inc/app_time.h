/*
 * app_time.h
 *
 *  Created on: 28 Eyl 2026
 *      Author: mucahit.aymaz
 */

#ifndef APP_TIME_H_
#define APP_TIME_H_

#include <stdint.h>

/* Starts TIM2 as a free-running 1 MHz counter. Call once before the scheduler starts. */
void     app_time_init(void);

/* Returns TIM2 counter in microseconds. Wraps every ~71.6 minutes. */
uint32_t timer_us(void);

#endif /* APP_TIME_H_ */
