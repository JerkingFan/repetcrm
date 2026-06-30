import { SharedArray } from "k6/data";
import { usersFile } from "./config.js";

/** Loaded once at init — k6 forbids open() inside VU functions. */
export const usersData = new SharedArray("loadtest_users", function () {
  const path = usersFile();
  try {
    return [JSON.parse(open(path))];
  } catch (e) {
    throw new Error(`Cannot read USERS_FILE=${path}: ${e}`);
  }
});

export function firstUser() {
  const payload = usersData[0];
  if (!payload?.users?.length) {
    throw new Error("users.json has no users — run seed script first");
  }
  return payload.users[0];
}

export function allUsers() {
  const payload = usersData[0];
  return payload?.users || [];
}
