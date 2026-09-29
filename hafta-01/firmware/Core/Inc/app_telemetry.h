#ifndef APP_TELEMETRY_H_
#define APP_TELEMETRY_H_

#include <stdint.h>
#include <stdbool.h>

/* SCN command: select scenario, reset log/counters/ids, wake TelemetryTask.
   Returns false for an invalid scenario number. */
bool telemetry_set_scenario(uint8_t scn);

/* STOP command: telemetry stops after its current period */
void telemetry_stop(void);

bool telemetry_is_running(void);

/* Calibration result: measured duration of CAL_ITERS work iterations, in us */
uint32_t telemetry_cal_us(void);

#endif /* APP_TELEMETRY_H_ */
