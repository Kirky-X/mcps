import asyncio
import json
import unittest
from unittest.mock import Mock, patch

import pytest
from mcp.types import TextContent, Tool
from time_master.core import TimeMaster

# Import the module under test
from time_master import mcp_service


class TestMCPService(unittest.TestCase):
    """Test cases for MCP service functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset the server and timemaster instances for each test
        self.original_timemaster = mcp_service.timemaster
        self.mock_timemaster = Mock(spec=TimeMaster)
        mcp_service.timemaster = self.mock_timemaster

    def tearDown(self):
        """Clean up after tests."""
        # Restore original timemaster
        mcp_service.timemaster = self.original_timemaster

    def test_list_tools(self):
        """Test list_tools function returns correct tool definitions."""
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tools = loop.run_until_complete(mcp_service.list_tools())
        finally:
            loop.close()

        # Verify tools are returned
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)

        # Check that all tools are Tool instances
        for tool in tools:
            self.assertIsInstance(tool, Tool)
            self.assertIsInstance(tool.name, str)
            self.assertIsInstance(tool.description, str)
            self.assertIsInstance(tool.inputSchema, dict)

        # Check specific tools exist
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_time",
            "get_local_timezone",
            "search_timezones",
            "calculate_time_difference",
            "search_holiday",
            "list_holidays"
        ]

        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)

    def test_tool_schemas(self):
        """Test that tool schemas are properly defined."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tools = loop.run_until_complete(mcp_service.list_tools())
        finally:
            loop.close()

        # Find get_time tool and verify its schema
        get_time_tool = next(tool for tool in tools if tool.name == "get_time")
        schema = get_time_tool.inputSchema

        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)

        properties = schema["properties"]
        self.assertIn("timezone", properties)
        self.assertIn("time_str", properties)
        self.assertIn("from_tz", properties)
        self.assertIn("format", properties)

        # Check calculate_time_difference has required fields
        calc_diff_tool = next(tool for tool in tools if tool.name == "calculate_time_difference")
        calc_schema = calc_diff_tool.inputSchema
        self.assertIn("required", calc_schema)
        self.assertEqual(set(calc_schema["required"]), {"time1", "tz1", "time2", "tz2"})


class TestMCPToolCalls(unittest.TestCase):
    """Test cases for MCP tool call handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_timemaster = mcp_service.timemaster
        self.mock_timemaster = Mock(spec=TimeMaster)
        mcp_service.timemaster = self.mock_timemaster

        # Set up event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up after tests."""
        mcp_service.timemaster = self.original_timemaster
        self.loop.close()

    def test_get_time_current(self):
        """Test get_time tool for current time."""
        # Mock timemaster methods
        self.mock_timemaster.get_time.return_value = "2024-06-15T12:00:00Z"
        self.mock_timemaster.get_local_timezone.return_value = "UTC"

        # Call the tool
        arguments = {"timezone": "UTC", "format": "iso"}
        result = self.loop.run_until_complete(
            mcp_service.call_tool("get_time", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn("Current time in UTC", result[0].text)
        self.assertIn("2024-06-15T12:00:00Z", result[0].text)

        # Verify timemaster was called correctly
        self.mock_timemaster.get_time.assert_called_once_with(
            timezone="UTC", time_str=None, from_tz=None, format="iso"
        )

    def test_get_time_conversion(self):
        """Test get_time tool for time conversion."""
        # Mock timemaster methods
        self.mock_timemaster.get_time.return_value = "2024-06-15T08:00:00-04:00"
        self.mock_timemaster.get_local_timezone.return_value = "America/New_York"

        # Call the tool with conversion parameters
        arguments = {
            "timezone": "America/New_York",
            "time_str": "2024-06-15T12:00:00Z",
            "from_tz": "UTC",
            "format": "iso"
        }
        result = self.loop.run_until_complete(
            mcp_service.call_tool("get_time", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn("Converted time", result[0].text)
        self.assertIn("2024-06-15T08:00:00-04:00", result[0].text)

        # Verify timemaster was called correctly
        self.mock_timemaster.get_time.assert_called_once_with(
            timezone="America/New_York",
            time_str="2024-06-15T12:00:00Z",
            from_tz="UTC",
            format="iso"
        )

    def test_get_local_timezone(self):
        """Test get_local_timezone tool."""
        # Mock timemaster method
        self.mock_timemaster.get_local_timezone.return_value = "America/New_York"

        # Call the tool
        result = self.loop.run_until_complete(
            mcp_service.call_tool("get_local_timezone", {})
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertEqual(result[0].text, "Local timezone: America/New_York")

        # Verify timemaster was called
        self.mock_timemaster.get_local_timezone.assert_called_once()

    def test_search_timezones_with_query(self):
        """Test search_timezones tool with query."""
        # Mock timemaster method
        self.mock_timemaster.find_timezones.return_value = [
            "America/New_York",
            "America/Chicago",
            "America/Denver"
        ]

        # Call the tool
        arguments = {"query": "America", "limit": 20}
        result = self.loop.run_until_complete(
            mcp_service.call_tool("search_timezones", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn("Matching timezones for 'America'", result[0].text)
        self.assertIn("America/New_York", result[0].text)

        # Verify timemaster was called correctly
        self.mock_timemaster.find_timezones.assert_called_once_with("America", limit=20)

    def test_search_timezones_empty_query(self):
        """Test search_timezones tool with empty query."""
        # Mock timemaster method and pytz
        self.mock_timemaster.find_timezones.return_value = [
            "UTC", "America/New_York", "Europe/London"
        ]

        with patch('time_master.mcp_service.pytz') as mock_pytz:
            mock_pytz.all_timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]

            # Call the tool
            arguments = {"query": "", "limit": 3}
            result = self.loop.run_until_complete(
                mcp_service.call_tool("search_timezones", arguments)
            )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn("All timezones", result[0].text)
        self.assertIn("... and 1 more", result[0].text)

    def test_search_timezones_no_matches(self):
        """Test search_timezones tool with no matches."""
        # Mock timemaster method
        self.mock_timemaster.find_timezones.return_value = []

        # Call the tool
        arguments = {"query": "NonExistent", "limit": 20}
        result = self.loop.run_until_complete(
            mcp_service.call_tool("search_timezones", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertEqual(result[0].text, "No timezones found matching 'NonExistent'")

    def test_calculate_time_difference(self):
        """Test calculate_time_difference tool."""
        # Mock timemaster method
        self.mock_timemaster.difference.return_value = "5 hours ahead"

        # Call the tool
        arguments = {
            "time1": "12:00",
            "tz1": "UTC",
            "time2": "07:00",
            "tz2": "America/New_York"
        }
        result = self.loop.run_until_complete(
            mcp_service.call_tool("calculate_time_difference", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn("Time difference between UTC and America/New_York", result[0].text)
        self.assertIn("5 hours ahead", result[0].text)

        # Verify timemaster was called correctly
        self.mock_timemaster.difference.assert_called_once_with("UTC", "America/New_York")

    def test_search_holiday(self):
        """Test search_holiday tool."""
        # Mock timemaster method
        mock_result = {
            "holidays": [
                {"name": "Independence Day", "date": "2024-07-04", "days_until": 19}
            ]
        }
        self.mock_timemaster.search_holiday.return_value = mock_result

        # Call the tool
        arguments = {
            "query": "Independence",
            "country": "US",
            "year": 2024,
            "limit": 10
        }
        result = self.loop.run_until_complete(
            mcp_service.call_tool("search_holiday", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)

        # Parse the JSON result
        result_data = json.loads(result[0].text)
        self.assertEqual(result_data, mock_result)

        # Verify timemaster was called correctly
        self.mock_timemaster.search_holiday.assert_called_once_with(
            query="Independence",
            country="US",
            timezone=None,
            year=2024,
            limit=10
        )

    def test_search_holiday_with_timezone(self):
        """Test search_holiday tool with timezone parameter."""
        # Mock timemaster method
        mock_result = {"holidays": []}
        self.mock_timemaster.search_holiday.return_value = mock_result

        # Call the tool
        arguments = {
            "query": "",
            "timezone": "America/New_York",
            "limit": 5
        }
        result = self.loop.run_until_complete(
            mcp_service.call_tool("search_holiday", arguments)
        )

        # Verify timemaster was called with timezone
        self.mock_timemaster.search_holiday.assert_called_once_with(
            query="",
            country=None,
            timezone="America/New_York",
            year=None,
            limit=5
        )

    def test_list_holidays(self):
        """Test list_holidays tool."""
        # Mock timemaster method
        mock_result = {
            "country": "US",
            "year": 2024,
            "holidays": [
                {"name": "New Year's Day", "date": "2024-01-01"},
                {"name": "Independence Day", "date": "2024-07-04"}
            ]
        }
        self.mock_timemaster.list_holidays.return_value = mock_result

        # Call the tool
        arguments = {"country": "US", "year": 2024}
        result = self.loop.run_until_complete(
            mcp_service.call_tool("list_holidays", arguments)
        )

        # Verify result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)

        # Parse the JSON result
        result_data = json.loads(result[0].text)
        self.assertEqual(result_data, mock_result)

        # Verify timemaster was called correctly
        self.mock_timemaster.list_holidays.assert_called_once_with(
            country="US",
            timezone=None,
            year=2024
        )

    def test_list_holidays_with_timezone(self):
        """Test list_holidays tool with timezone parameter."""
        # Mock timemaster method
        mock_result = {"holidays": []}
        self.mock_timemaster.list_holidays.return_value = mock_result

        # Call the tool
        arguments = {"timezone": "Europe/London"}
        result = self.loop.run_until_complete(
            mcp_service.call_tool("list_holidays", arguments)
        )

        # Verify timemaster was called with timezone
        self.mock_timemaster.list_holidays.assert_called_once_with(
            country=None,
            timezone="Europe/London",
            year=None
        )

    def test_unknown_tool(self):
        """Test handling of unknown tool names."""
        # Call with unknown tool name
        result = self.loop.run_until_complete(
            mcp_service.call_tool("unknown_tool", {})
        )

        # Verify error response
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertEqual(result[0].text, "Unknown tool: unknown_tool")

    def test_tool_exception_handling(self):
        """Test exception handling in tool calls."""
        # Mock timemaster to raise an exception
        self.mock_timemaster.get_local_timezone.side_effect = Exception("Test error")

        # Call the tool
        result = self.loop.run_until_complete(
            mcp_service.call_tool("get_local_timezone", {})
        )

        # Verify error response
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextContent)
        self.assertIn("Error executing tool 'get_local_timezone'", result[0].text)
        self.assertIn("Test error", result[0].text)


class TestMCPServiceUtilities(unittest.TestCase):
    """Test cases for MCP service utility functions."""

    @patch('time_master.mcp_service.os.chdir')
    @patch('time_master.mcp_service.Path')
    @patch('time_master.mcp_service.logger')
    def test_setup_working_directory_success(self, mock_logger, mock_path, mock_chdir):
        """Test successful working directory setup."""
        # Mock Path behavior
        mock_file_path = Mock()
        mock_parent = Mock()
        mock_timemaster_root = Mock()

        mock_file_path.parent = mock_parent
        mock_parent.parent = mock_timemaster_root
        mock_path.return_value = mock_file_path
        mock_path.__file__ = "/path/to/time_master/src/time_master/mcp_service.py"

        # Call the function
        mcp_service.setup_working_directory()

        # Verify chdir was called
        mock_chdir.assert_called_once_with(mock_timemaster_root)
        mock_logger.info.assert_called_once()

    @patch('time_master.mcp_service.os.chdir')
    @patch('time_master.mcp_service.Path')
    @patch('time_master.mcp_service.logger')
    def test_setup_working_directory_failure(self, mock_logger, mock_path, mock_chdir):
        """Test working directory setup failure handling."""
        # Mock chdir to raise an exception
        mock_chdir.side_effect = Exception("Permission denied")

        # Call the function
        mcp_service.setup_working_directory()

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_called_once_with("Continuing with current working directory")

    @patch('time_master.mcp_service.asyncio.run')
    def test_async_main(self, mock_run):
        """Test async_main function."""
        # Call the function
        mcp_service.async_main()

        # Verify asyncio.run was called with main() coroutine
        mock_run.assert_called_once()
        # Check that the argument is a coroutine
        call_args = mock_run.call_args[0][0]
        self.assertTrue(hasattr(call_args, '__await__'))


class TestMCPServiceIntegration(unittest.TestCase):
    """Integration tests for MCP service."""

    def setUp(self):
        """Set up test fixtures."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()

    def test_tool_list_and_call_integration(self):
        """Test integration between list_tools and call_tool."""
        # Get the list of tools
        tools = self.loop.run_until_complete(mcp_service.list_tools())

        # Verify we can call each tool (with mocked timemaster)
        with patch.object(mcp_service, 'timemaster') as mock_timemaster:
            mock_timemaster.get_local_timezone.return_value = "UTC"
            mock_timemaster.get_time.return_value = "2024-06-15T12:00:00Z"
            mock_timemaster.find_timezones.return_value = ["UTC"]
            mock_timemaster.difference.return_value = "0 hours"
            mock_timemaster.search_holiday.return_value = {"holidays": []}
            mock_timemaster.list_holidays.return_value = {"holidays": []}

            for tool in tools:
                # Prepare minimal arguments for each tool
                if tool.name == "get_time":
                    args = {}
                elif tool.name == "get_local_timezone":
                    args = {}
                elif tool.name == "search_timezones":
                    args = {"query": "UTC"}
                elif tool.name == "calculate_time_difference":
                    args = {"time1": "12:00", "tz1": "UTC", "time2": "12:00", "tz2": "UTC"}
                elif tool.name == "search_holiday":
                    args = {"query": "test"}
                elif tool.name == "list_holidays":
                    args = {"country": "US"}
                else:
                    continue

                # Call the tool and verify it returns a result
                result = self.loop.run_until_complete(
                    mcp_service.call_tool(tool.name, args)
                )

                self.assertIsInstance(result, list)
                self.assertGreater(len(result), 0)
                self.assertIsInstance(result[0], TextContent)


if __name__ == '__main__':
    unittest.main()
