JsOsaDAS1.001.00bplist00�Vscript_�// set things up
var app = Application('Reminders');
app.includeStandardAdditions = true;

var reminder = app.reminders.byId("x-apple-reminder://5A83B7B6-25DC-4190-B7F5-7BE5E921F527");
console.log(reminder.properties());
reminder.setDueDate(false);
                              jscr  ��ޭ