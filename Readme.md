# Alert Wrapper #

Provides an scripting interface that will send an alert when the wrapped program or process either finishes successfully or errors out.

An alert can be sent to an email or phone number (via sms).

Some things which this wrapper will not do at the moment:

+ perform multiple runs
+ Automatically rerun command if an error occurs
+ provide custom messages

## Output Message ##

A successfully run command will send the following message: `Command completed successfully @ <time>`

A command which errors out will have a message like: `Command failed @ <time> with return code X`

`<time>` will be a formatted data-time like this: `Tue Nov 24 1423h`

## Usage ##

```
prog_monitor {--email [<address>]| --sms [<number>]} [--from <sending address>] -- <user_command>
```