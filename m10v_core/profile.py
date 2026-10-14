"""Facts verified against the exact local official GR III firmware.

These facts permit inspection only. They authorize no patch or camera write.
Section payload lengths exclude the 16-byte header (also for RES).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SectionRule:
    name: str
    payload_bytes: int
    flags: int
    resource_count: int | None = None


@dataclass(frozen=True)
class VersionSite:
    name: str
    region: str
    region_id: str | None
    offset: int
    byteorder: str
    expected_bytes: bytes


@dataclass(frozen=True)
class WordSumEvidence:
    """Proven complete-payload sum, without an inferred repair location."""
    partition: str
    byteorder: str
    word_bytes: int
    modulus: int
    expected_sum: int


@dataclass(frozen=True)
class ExecutableRangeEvidence:
    """Profile-owned static mode/boundary proof bound to exact source bytes.

    A patch request cannot supply this proof. Adding a real range requires
    independent disassembly/control-flow evidence for the exact profile SHA.
    """
    partition: str
    offset: int
    mode: str
    expected_bytes: bytes
    evidence_id: str

    def __post_init__(self):
        stride = {'ARM': 4, 'Thumb': 2}.get(self.mode)
        if (type(self.partition) is not str or type(self.offset) is not int or
                stride is None or self.offset < 0 or self.offset % stride or
                type(self.expected_bytes) is not bytes or not self.expected_bytes or
                len(self.expected_bytes) % stride or type(self.evidence_id) is not str or
                not self.evidence_id.strip()):
            raise ValueError('invalid independent executable range evidence')


@dataclass(frozen=True)
class GR3Profile:
    profile_id: str = 'gr3'
    model: str = 'GR III'
    filename: str = 'fwdc239b.bin'
    sha256: str = 'd6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4'
    file_size: int = 30391780
    project: int = 588
    project_copy: int = 0x024C024C
    marker: int = 0xA55A5AA5
    firmware_type: int = 2
    metadata_record_count: int = 0
    metadata_length: int = 0
    container_header_size: int = 128
    decoded_size: int = 59718388
    section_header_size: int = 16
    decoded_checksum_size: int = 4
    rtos_size: int = 17520064
    rtos_sha256: str = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
    rtos_base: int = 0x53000000
    startup_offset: int = 0x450
    startup_copy: tuple[int, int, int] = (0x5407B540, 0x55000000, 0x3A080)
    version_word: int = 0x020A151B
    internal_version: str = '2.10.21.27'
    public_version: str = '2.10'
    rtos_version_offset: int = 0x2038
    cpu_version_offset: int = 0x90
    version_byteorder: str = 'big'
    outer_version_offsets: tuple[tuple[str, int], ...] = (('outer_cpu', 0x38), ('outer_dsp', 0x50))
    # RTOS load bounds alone do not prove ARM/Thumb mode or executable regions.
    executable_ranges: tuple[ExecutableRangeEvidence, ...] = ()
    version_sites: tuple[VersionSite, ...] = (
        VersionSite('rtos', 'PARTITION', 'RTOS', 0x2038, 'big', b'\x02\x0a\x15\x1b'),
        VersionSite('cpu', 'PARTITION', 'CPU', 0x90, 'big', b'\x02\x0a\x15\x1b'),
        VersionSite('outer_cpu', 'CONTAINER_RAW', None, 0x38, 'big', b'\x02\x0a\x15\x1b'),
        VersionSite('outer_dsp', 'CONTAINER_RAW', None, 0x50, 'big', b'\x02\x0a\x15\x1b'),
    )
    checksum_evidence: tuple[WordSumEvidence, ...] = (
        WordSumEvidence('CPU', 'big', 4, 2**32, 0),
        WordSumEvidence('RTOS', 'little', 4, 2**32, 0x3010FFA5),
        WordSumEvidence('SRIC', 'little', 4, 2**32, 0x96D7AAD7),
    )
    sections: tuple[SectionRule, ...] = (
        SectionRule('BOOTPARA', 72, 0xFFFF0005),
        SectionRule('DRAMPARA', 556, 0xFFFF0001),
        SectionRule('PARTPARA', 516, 0xFFFF0002),
        SectionRule('M0', 44640, 3),
        SectionRule('BOOT', 21816, 4),
        SectionRule('RTOS', 17520064, 0x10004),
        SectionRule('LINUX', 3062784, 0x50004),
        SectionRule('INITFS', 13899776, 0x60004),
        SectionRule('SRIC', 49152, 0x20004),
        SectionRule('CPU', 131072, 7),
        SectionRule('SHELLCMD', 37440, 0x30004),
        SectionRule('ICONBIN', 18354964, 0x40004),
        SectionRule('FDRVPARA', 36, 0xFFFF0008),
        SectionRule('RES', 6595272, 0xFFFF0006, 35),
    )

    @property
    def section_order(self) -> tuple[str, ...]:
        return tuple(rule.name for rule in self.sections)


GR3 = GR3Profile()
