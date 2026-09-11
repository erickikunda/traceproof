#include <stdlib.h>
int main(int count, char **arguments) {
 if (count > 1) {
  const char *command = arguments[1];
  return system("echo fixed");
 }
 return 0;
}
