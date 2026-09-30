"""
Phase 2b (rebuild): drop + recreate MySQL lab_results with the right schema.
The previous version was missing loinc_category, age, gender (denormalized for Power BI),
and the display_range column was too narrow (VARCHAR(100) for max=662 chars).
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_URL = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    f"?charset=utf8mb4"
)
engine = create_engine(DB_URL)

DDL = """
CREATE TABLE lab_results (
    id             BIGINT        NOT NULL AUTO_INCREMENT,
    document_id    VARCHAR(32)   NOT NULL,
    age            TINYINT UNSIGNED,
    gender         VARCHAR(10),
    loinc          VARCHAR(20),
    loinc_category VARCHAR(30),
    test_name_raw  VARCHAR(200)  NOT NULL,
    value_raw      VARCHAR(255)  NOT NULL,
    value_num      DECIMAL(15,5),
    is_numeric     TINYINT(1)    NOT NULL DEFAULT 0,
    unit           VARCHAR(20),
    specimen       VARCHAR(50),
    display_range  VARCHAR(700),
    PRIMARY KEY (id),
    INDEX idx_doc          (document_id),
    INDEX idx_loinc        (loinc),
    INDEX idx_category     (loinc_category),
    INDEX idx_doc_loinc    (document_id, loinc),
    INDEX idx_age_gender   (age, gender)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

with engine.begin() as c:
    c.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    c.execute(text("DROP TABLE IF EXISTS lab_results"))
    c.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    c.execute(text(DDL))
    cols = c.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'lab_results'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()

print("MySQL lab_results recreated with columns:")
for col in cols:
    print(f"  {col[0]:20s} {col[1]:20s} {col[2] or ''}")
print("\npatients and loinc_dictionary tables left untouched.")
