#include <stdlib.h>
int helper(int count, char **arguments) {
 if (count > 1) {
  const char *command = arguments[1];
  return system(command);
 }
 return 0;
}
