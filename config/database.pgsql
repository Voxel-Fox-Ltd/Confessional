DROP DATABASE IF EXISTS BOTNAME;
CREATE DATABASE BOTNAME;
USE BOTNAME;

CREATE TABLE command_log(
    guild_id BIGINT,
    channel_id BIGINT,
    user_id BIGINT, 
    message_id BIGINT PRIMARY KEY,
    content VARCHAR(2000),
    command_name VARCHAR(100),
    invoked_with VARCHAR(100),
    command_prefix VARCHAR(2000),
    timestamp TIMESTAMP
);


CREATE TABLE confession_channel(
    code VARCHAR(5) PRIMARY KEY,
    channel_id BIGINT
);


CREATE TABLE banned_users(
    guild_id BIGINT,
    user_id BIGINT,
    PRIMARY KEY (guild_id, user_id)
);


CREATE TABLE confession_log(
    confession_message_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT,
    channel_code VARCHAR(5),
    channel_id BIGINT,
    timestamp TIMESTAMP,
    confession TEXT
);
