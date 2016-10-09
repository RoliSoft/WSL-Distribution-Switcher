/*

	Small library to read and write NTFS extended attributes.
	See ntfsea.py for a helper class to use it from Python.

	Part of the https://github.com/RoliSoft/WSL-Distribution-Switcher
	project, licensed under the MIT license.

*/

#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS

#define WIN32_NO_STATUS
#include <Windows.h>
#undef WIN32_NO_STATUS

#include <winternl.h>
#include <ntstatus.h>
#include <tchar.h>
#include <stdlib.h>
#include <stdio.h>

#define DLL_EXPORT __declspec(dllexport)

#define MAX_LIST_LEN 4096
#define MAX_EA_VALUE 256

#define MAX_GETEA (sizeof(FILE_GET_EA_INFORMATION) + MAX_EA_VALUE)
#define MAX_FULLEA (sizeof(FILE_FULL_EA_INFORMATION) + 2 * MAX_EA_VALUE)

typedef struct _FILE_EA_INFORMATION
{
	ULONG EaSize;
} FILE_EA_INFORMATION, *PFILE_EA_INFORMATION;

typedef struct _FILE_FULL_EA_INFORMATION
{
	ULONG NextEntryOffset;
	UCHAR Flags;
	UCHAR EaNameLength;
	USHORT EaValueLength;
	CHAR EaName[1];
} FILE_FULL_EA_INFORMATION, *PFILE_FULL_EA_INFORMATION;

typedef struct _FILE_GET_EA_INFORMATION
{
	ULONG NextEntryOffset;
	UCHAR EaNameLength;
	CHAR EaName[1];
} FILE_GET_EA_INFORMATION, *PFILE_GET_EA_INFORMATION;

typedef struct _RTL_RELATIVE_NAME_U
{
	UNICODE_STRING RelativeName;
	HANDLE ContainingDirectory;
	PVOID CurDirRef;
} RTL_RELATIVE_NAME_U, *PRTL_RELATIVE_NAME_U;

NTSYSAPI BOOLEAN NTAPI RtlDosPathNameToNtPathName_U(
	_In_ PWSTR DosFileName,
	_Out_ PUNICODE_STRING NtFileName,
	_Out_opt_ PWSTR* FilePart,
	_Out_opt_ PRTL_RELATIVE_NAME_U RelativeName
);

struct Ea
{
	CHAR Name[MAX_EA_VALUE];
	ULONG32 ValueLength;
	CHAR Value[MAX_EA_VALUE];
};

struct EaList
{
	ULONG32 ListSize;
	struct Ea List[MAX_LIST_LEN];
};

/*!
 * Opens the requested file for reading or writing.
 *
 * \param DosFileName Path to the file in wide-string format.
 * \param Write       Value indicating whether to open for writing.
 * \param EaBuffer    Pointer to allocated memory for the extended attributes information.
 * \param EaLength    Length of the extended attributes information.
 *
 * \return Handle to the opened file pointer or NULL on failure.
 */
HANDLE GetFileHandle(PWSTR DosFileName, BOOL Write, PFILE_FULL_EA_INFORMATION EaBuffer, PULONG EaLength)
{
	UNICODE_STRING FileName;
	OBJECT_ATTRIBUTES ObjectAttributes;
	ACCESS_MASK DesiredAccess = GENERIC_READ;
	HANDLE FileHandle;
	IO_STATUS_BLOCK IoStatusBlock;

	if (Write)
	{
		DesiredAccess |= GENERIC_WRITE;
	}

	if (!RtlDosPathNameToNtPathName_U(DosFileName, &FileName, NULL, NULL))
	{
		return NULL;
	}

	InitializeObjectAttributes(&ObjectAttributes, &FileName, 0, NULL, NULL);

	if (NtCreateFile(&FileHandle, DesiredAccess, &ObjectAttributes, &IoStatusBlock, NULL, 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, FILE_OPEN_IF, 0, EaBuffer, EaLength))
	{
		return NULL;
	}

	return FileHandle;
}

/*!
 * Fetches the list of extended attributes available on the requested file.
 *
 * \param FileName Path to the file in wide-string format.
 *
 * \return List of extended attributes or an empty list on error.
 */
DLL_EXPORT struct EaList* GetEaList(PWSTR FileName)
{
	NTSTATUS Status = 0;
	HANDLE FileHandle;
	IO_STATUS_BLOCK IoStatusBlock = { 0 };
	CHAR Buffer[MAX_LIST_LEN];
	PFILE_FULL_EA_INFORMATION EaBuffer;
	BOOLEAN RestartScan = TRUE;
	struct EaList* Result = (struct EaList*)malloc(sizeof(struct EaList));

	FileHandle = GetFileHandle(FileName, FALSE, NULL, 0);
	if (FileHandle == NULL)
	{
		return Result;
	}

	do
	{
		EaBuffer = (PFILE_FULL_EA_INFORMATION)Buffer;

		Status = NtQueryEaFile(FileHandle, &IoStatusBlock, EaBuffer, MAX_LIST_LEN, FALSE, NULL, 0, NULL, RestartScan);
		if (Status != STATUS_SUCCESS && Status != STATUS_BUFFER_OVERFLOW)
		{
			NtClose(FileHandle);
			return Result;
		}

		while (EaBuffer)
		{
			strcpy_s(Result->List[Result->ListSize].Name, MAX_EA_VALUE, EaBuffer->EaName);
			memcpy_s(Result->List[Result->ListSize].Value, MAX_EA_VALUE, EaBuffer->EaName + EaBuffer->EaNameLength + 1, EaBuffer->EaValueLength);
			Result->List[Result->ListSize].ValueLength = EaBuffer->EaValueLength;
			Result->ListSize++;

			if (EaBuffer->NextEntryOffset == 0)
			{
				break;
			}

			EaBuffer = (PFILE_FULL_EA_INFORMATION)((PCHAR)EaBuffer + EaBuffer->NextEntryOffset);
		}

		RestartScan = FALSE;
	}
	while (Status == STATUS_BUFFER_OVERFLOW);

	NtClose(FileHandle);

	return Result;
}

/*!
 * Fetches the specified extended attribute and its value from the requested file.
 *
 * \param FileName Path to the file in wide-string format.
 * \param EaName   Name of the extended attribute in a null-terminated string.
 *
 * \return Extended attribute information or empty structure on error.
 */
DLL_EXPORT struct Ea* GetEa(PWSTR FileName, PSTR EaName)
{
	NTSTATUS Status = 0;
	HANDLE FileHandle;
	IO_STATUS_BLOCK IoStatusBlock = { 0 };
	CHAR GetBuffer[MAX_LIST_LEN] = { 0 };
	CHAR FullBuffer[MAX_LIST_LEN] = { 0 };
	PFILE_GET_EA_INFORMATION EaList = (PFILE_GET_EA_INFORMATION)GetBuffer;
	PFILE_GET_EA_INFORMATION EaQuery = EaList;
	PFILE_FULL_EA_INFORMATION EaBuffer = (PFILE_FULL_EA_INFORMATION)FullBuffer;
	ULONG EaListLength = 0;
	ULONG EaNameLength = strlen(EaName);
	struct Ea* Result = (struct Ea*)malloc(sizeof(struct Ea));

	FileHandle = GetFileHandle(FileName, FALSE, NULL, 0);
	if (FileHandle == NULL)
	{
		return Result;
	}

	EaNameLength = (ULONG)((EaNameLength + 1) * sizeof(CHAR));
	memcpy_s(EaQuery->EaName, EaNameLength, EaName, EaNameLength);
	EaQuery->EaNameLength = (UCHAR)EaNameLength - sizeof(CHAR);

	EaQuery->NextEntryOffset = FIELD_OFFSET(FILE_GET_EA_INFORMATION, EaName) + EaQuery->EaNameLength + sizeof(CHAR);
	EaListLength += EaQuery->NextEntryOffset;
	EaQuery->NextEntryOffset = 0;

	EaQuery = (PFILE_GET_EA_INFORMATION)((PCHAR)EaQuery + EaQuery->NextEntryOffset);

	Status = NtQueryEaFile(FileHandle, &IoStatusBlock, EaBuffer, MAX_FULLEA, FALSE, EaList, EaListLength, NULL, TRUE);
	if (Status != STATUS_SUCCESS)
	{
		NtClose(FileHandle);
		return Result;
	}

	if (EaBuffer && EaBuffer->EaValueLength > 0)
	{
		strcpy_s(Result->Name, MAX_EA_VALUE, EaBuffer->EaName);
		memcpy_s(Result->Value, MAX_EA_VALUE, EaBuffer->EaName + EaBuffer->EaNameLength + 1, EaBuffer->EaValueLength);
		Result->ValueLength = EaBuffer->EaValueLength;
	}

	NtClose(FileHandle);

	return Result;
}

/*!
 * Writes the specified extended attribute and its value to the requested file.
 *
 * \param FileName      Path to the file in wide-string format.
 * \param EaName        Name of the extended attribute in a null-terminated string.
 * \param EaValue       Value of the extended attribute.
 * \param EaValueLength Length of the extended attribute value.
 *
 * \return Number of bytes written (should match EaValueLength) or -1 on failure.
 */
DLL_EXPORT LONG32 WriteEa(PWSTR FileName, PSTR EaName, PSTR EaValue, ULONG32 EaValueLength)
{
	HANDLE FileHandle;
	ULONG EaNameLength = strlen(EaName);
	CHAR Buffer[MAX_FULLEA] = { 0 };
	IO_STATUS_BLOCK IoStatusBlock = { 0 };
	PFILE_FULL_EA_INFORMATION EaBuffer = NULL;
	ULONG EaLength = 0;

	FileHandle = GetFileHandle(FileName, TRUE, EaBuffer, &EaLength);
	if (FileHandle == NULL)
	{
		return -1;
	}

	EaBuffer = (PFILE_FULL_EA_INFORMATION)Buffer;
	EaBuffer->NextEntryOffset = 0;
	EaBuffer->Flags = 0;

	EaNameLength = (ULONG)((EaNameLength + 1) * sizeof(CHAR));
	memcpy_s(EaBuffer->EaName, EaNameLength, EaName, EaNameLength);
	EaBuffer->EaNameLength = (UCHAR)EaNameLength - sizeof(CHAR);

	if (EaValue == NULL)
	{
		EaBuffer->EaValueLength = 0;
	}
	else
	{
		EaValueLength = (ULONG)((EaValueLength + 1) * sizeof(CHAR));
		memcpy_s(EaBuffer->EaName + EaBuffer->EaNameLength + sizeof(CHAR), EaValueLength, EaValue, EaValueLength);
		EaBuffer->EaValueLength = EaValueLength - sizeof(CHAR);
	}

	EaLength = FIELD_OFFSET(FILE_FULL_EA_INFORMATION, EaName) + EaBuffer->EaNameLength + sizeof(CHAR) + EaBuffer->EaValueLength;

	if (NtSetEaFile(FileHandle, &IoStatusBlock, EaBuffer, EaLength))
	{
		NtClose(FileHandle);
		return -1;
	}

	NtClose(FileHandle);

	return EaBuffer->EaValueLength;
}
