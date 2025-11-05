# This file has been removed as the tests were testing the old architecture
# where the content generator was expected to execute tools directly.
# After our refactor, tool execution is handled by the turn manager,
# and the content generator only generates responses with tool calls
# but doesn't execute them.