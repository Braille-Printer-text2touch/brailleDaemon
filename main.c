#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "main.h"

/* void daemonize(void) {
  pid_t pid = fork(); // fork once to remove from current session group
  if (pid < 0)
    exit(EXIT_FAILURE); // fork failed
  if (pid > 0)
    exit(EXIT_SUCCESS); // kill the parent who is in the session group/

  // make into a new session group
  if (setsid() < 0)
    exit(EXIT_FAILURE);

  pid = fork(); // fork twice to no longer be attached to a controlling terminal
  if (pid < 0)
    exit(EXIT_FAILURE);
  if (pid > 0)
    exit(EXIT_SUCCESS);

  umask(0); // make sure there's no creation mask when we're working

  if (chdir("/") < 0) // move to root
    exit(EXIT_FAILURE);

  close(STDIN_FILENO);
  close(STDOUT_FILENO);
  close(STDERR_FILENO);
} */

void processPipeInfo(char *buffer) {
  for (; *buffer; buffer++)
    putc(*buffer, stdout);
}

#ifndef TESTING
int main(void) {
  // daemonize this process, change to root, and close the standard file streams
  daemon(0, 0);
  umask(0); // make sure there's no creation mask when we're working

  if (mkfifo(PIPE_PATH, 0666) < 0 && errno != EEXIST) {
    // if the pipe making failed and it's not because the pipe just already
    // exists
    perror("making pipe");
    exit(EXIT_FAILURE);
  }

  int pipeDescriptor = open(PIPE_PATH, O_RDONLY);
  if (pipeDescriptor < 0) {
    // open the pipe for reading
    perror("opening pip");
    exit(EXIT_FAILURE);
  }

  char buffer[BUFFER_SIZE];
  ssize_t bytesRead; // signed size for counting bytes we got

  while (1) {
    bytesRead = read(pipeDescriptor, buffer, sizeof(buffer) - 1);
    if (bytesRead >= 0) {
      buffer[bytesRead] = '\0'; // terminate whatever chunk we got
      processPipeInfo(buffer);
    } else {
      perror("reading from pipe");
    }
  }

  close(pipeDescriptor);

  return EXIT_SUCCESS;
}
#endif
