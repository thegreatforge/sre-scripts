import re

POSTGRES_LOG_REGEX = r'(\d+-\d+-\d+\s+\d+:\d+:\d+\s+UTC):(\d+.\d+.\d+.\d+)\(\d+\):(\w+)@(\w+):\[\d+\]:\w+:\s+duration:\s+(\d+.\d+)\s+ms\s+(.*)'

def parse_log_line(date, line):
    if line.startswith(date):
        parsed_data = re.findall(POSTGRES_LOG_REGEX, line)
        if len(parsed_data):
            p = PostgresLogModel(*parsed_data[0])
            if p.should_consider():
                return p
    return None


class PostgresLogModel:
    def __init__(self, *args):
        self.time = args[0]
        self.ipv4 = args[1]
        self.user = args[2]
        self.database = args[3]
        self.duration = args[4]
        self.statement = args[5]
    
    def should_consider(self):
        if self.user in ["pgwatch_monitor"]:
            return False
        return True
    
    def get_statement(self):
        return self.statement

    def get_duration(self):
        return float(self.duration)
