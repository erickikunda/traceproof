#include "probe.h"
int main(int count, char **arguments) {
 if (count > 1) {
  const char *command = arguments[1];
  return dispatch(command);
 }
 return 0;
}
