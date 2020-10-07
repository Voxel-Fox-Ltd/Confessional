CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(30)
);


CREATE TABLE IF NOT EXISTS user_settings(
    user_id BIGINT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS role_list(
    guild_id BIGINT,
    role_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, role_id, key)
);


CREATE TABLE IF NOT EXISTS channel_list(
    guild_id BIGINT,
    channel_id BIGINT,
    key VARCHAR(50),
    value VARCHAR(50),
    PRIMARY KEY (guild_id, channel_id, key)
);


CREATE TABLE IF NOT EXISTS confession_channel(
    code VARCHAR(5) PRIMARY KEY,
    channel_id BIGINT
);


CREATE TABLE IF NOT EXISTS banned_users(
    guild_id BIGINT,
    user_id BIGINT,
    PRIMARY KEY (guild_id, user_id)
);


CREATE TABLE IF NOT EXISTS confession_log(
    confession_message_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT,
    channel_code VARCHAR(5),
    channel_id BIGINT,
    timestamp TIMESTAMP,
    confession TEXT,
    ban_code VARCHAR(16)
);
