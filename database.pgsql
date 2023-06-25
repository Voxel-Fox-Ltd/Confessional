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
